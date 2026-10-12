from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from cart.models import Cart

from .forms import CheckoutForm
from .models import Coupon, Order, OrderItem, Payment


def _compute_totals(cart, coupon):
    """Recalculate every amount on the server using database prices."""
    subtotal = sum((item.line_total for item in cart.items.all()), start=Decimal('0.00'))
    discount = Decimal('0.00')
    if coupon is not None:
        ok, _ = coupon.is_valid_for(subtotal)
        if ok:
            discount = coupon.discount_for(subtotal)
    discountable = subtotal - discount
    shipping = Decimal('0.00') if (discountable == 0 or discountable >= settings.FREE_SHIPPING_THRESHOLD) \
        else Decimal(settings.DEFAULT_SHIPPING_FEE)
    total = max(discountable, Decimal('0.00')) + shipping
    return subtotal, discount, shipping, total


def _get_active_coupon(request):
    code = request.session.get('coupon_code')
    if not code:
        return None
    return Coupon.objects.filter(code=code, is_active=True).first()


@login_required
@require_http_methods(['GET', 'POST'])
def checkout(request):
    cart = Cart.objects.filter(user=request.user).first()
    items = cart.items.select_related('product', 'variant').all() if cart else []
    if not items:
        messages.info(request, 'Your cart is empty — add something you love first.')
        return redirect('catalog:shop')

    coupon = _get_active_coupon(request)
    subtotal, discount, shipping, total = _compute_totals(cart, coupon)

    out_of_stock = [i for i in items if not i.is_available]
    if out_of_stock:
        for item in out_of_stock:
            messages.error(request, f'"{item.product.name}" is out of stock. Please adjust your cart.')
        return redirect('cart:detail')

    # Prefill from the user's profile / default address.
    user = request.user
    default_address = user.addresses.filter(is_default=True).first() or user.addresses.first()
    initial = {
        'full_name': user.full_name,
        'phone': user.phone,
    }
    if default_address:
        initial.update({
            'full_name': default_address.full_name,
            'phone': default_address.phone,
            'address_line1': default_address.line1,
            'address_line2': default_address.line2,
            'city': default_address.city,
            'state': default_address.state,
            'pincode': default_address.pincode,
        })

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            return _place_order(request, cart, form, coupon, subtotal, discount, shipping, total)
        messages.error(request, 'Please correct the errors in the checkout form.')
    else:
        form = CheckoutForm(initial=initial)

    context = {
        'form': form,
        'items': items,
        'subtotal': subtotal,
        'discount': discount,
        'shipping': shipping,
        'total': total,
        'coupon': coupon,
        'free_shipping_threshold': settings.FREE_SHIPPING_THRESHOLD,
        'shipping_needed': settings.DEFAULT_SHIPPING_FEE,
    }
    return render(request, 'orders/checkout.html', context)


def _place_order(request, cart, form, coupon, subtotal, discount, shipping, total):
    """Create the order atomically, validating and decrementing stock."""
    try:
        with transaction.atomic():
            # Lock cart + stock rows while we validate (select_for_update is a
            # no-op on SQLite but protects us on PostgreSQL in production).
            items = list(
                cart.items.select_for_update().select_related('product', 'variant')
            )

            # Re-validate stock inside the transaction.
            for item in items:
                available = item.available_stock
                if item.quantity > available:
                    messages.error(
                        request,
                        f'Only {available} left of "{item.product.name}" '
                        f'({item.size} {item.color}) — please adjust your cart.',
                    )
                    raise InsufficientStock()

            # Re-read prices from the database — never trust the browser.
            subtotal, discount, shipping, total = _compute_totals(cart, coupon)
            if subtotal <= 0:
                messages.error(request, 'Your cart is empty.')
                raise InsufficientStock()

            order = form.save(commit=False)
            order.user = request.user
            order.subtotal = subtotal
            order.discount_amount = discount
            order.shipping_amount = shipping
            order.total = total
            order.coupon = coupon if discount > 0 else None
            order.status = Order.STATUS_PENDING
            order.save()

            for item in items:
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    variant=item.variant,
                    product_name=item.product.name,
                    size=item.size,
                    color=item.color,
                    unit_price=item.unit_price,  # price captured at purchase time
                    quantity=item.quantity,
                )
                # Decrement stock safely.
                if item.variant_id:
                    item.variant.stock -= item.quantity
                    item.variant.save(update_fields=['stock'])
                item.product.stock = max(0, item.product.stock - item.quantity)
                item.product.sales_count += item.quantity
                item.product.save(update_fields=['stock', 'sales_count'])

            # Payment record — status only reflects what actually happened.
            if order.payment_method == 'demo':
                payment = Payment.objects.create(
                    order=order,
                    amount=total,
                    method='demo',
                    status=Payment.STATUS_PENDING,
                    is_demo=True,
                    reference=f'DEMO-{order.order_number}',
                )
            else:
                payment = Payment.objects.create(
                    order=order,
                    amount=total,
                    method='cod',
                    status=Payment.STATUS_PENDING,
                    is_demo=True,
                    reference='Pay on delivery',
                )

            cart.items.all().delete()
            request.session.pop('coupon_code', None)

    except InsufficientStock:
        return redirect('cart:detail')

    messages.success(request, f'Order {order.order_number} placed successfully!')
    return redirect('orders:detail', order_number=order.order_number)


class InsufficientStock(Exception):
    """Raised inside the order transaction to trigger a rollback."""


@login_required
def order_history(request):
    orders = request.user.orders.all()
    return render(request, 'orders/history.html', {'orders': orders})


@login_required
def order_detail(request, order_number):
    order = get_object_or_404(
        Order.objects.prefetch_related('items', 'payment'),
        order_number=order_number,
        user=request.user,  # ownership enforced — users cannot see others' orders
    )
    payment = getattr(order, 'payment', None)
    return render(request, 'orders/detail.html', {'order': order, 'payment': payment})


@login_required
@require_http_methods(['POST'])
def cancel_order(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    if not order.can_cancel:
        messages.error(
            request,
            f'Order {order.order_number} can no longer be cancelled '
            f'(status: {order.status}). Please contact support.',
        )
        return redirect('orders:detail', order_number=order.order_number)

    with transaction.atomic():
        order = Order.objects.select_for_update().get(pk=order.pk)
        if not order.can_cancel:
            messages.error(request, 'This order was just updated and can no longer be cancelled.')
            return redirect('orders:detail', order_number=order.order_number)

        # Restore stock.
        for item in order.items.all():
            if item.variant_id:
                item.variant.stock += item.quantity
                item.variant.save(update_fields=['stock'])
            item.product.stock += item.quantity
            item.product.sales_count = max(0, item.product.sales_count - item.quantity)
            item.product.save(update_fields=['stock', 'sales_count'])

        order.status = Order.STATUS_CANCELLED
        order.save(update_fields=['status', 'updated_at'])

        # Reflect cancellation on the payment record too.
        if hasattr(order, 'payment'):
            payment = order.payment
            if payment.status == Payment.STATUS_PAID:
                payment.status = Payment.STATUS_REFUNDED
            payment.reference = (payment.reference + ' | Cancelled').strip(' |')
            payment.save(update_fields=['status', 'reference', 'updated_at'])

    messages.success(request, f'Order {order.order_number} has been cancelled and stock restored.')
    return redirect('orders:detail', order_number=order.order_number)
