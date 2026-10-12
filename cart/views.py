from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from catalog.models import Product, ProductVariant
from orders.models import Coupon

from .models import Cart, CartItem


def _get_cart(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    return cart


def _safe_next(request):
    nxt = request.POST.get('next', '')
    if nxt and nxt.startswith('/') and not nxt.startswith('//'):
        return nxt
    return None


@login_required
@require_http_methods(['GET'])
def cart_detail(request):
    cart = _get_cart(request)
    items = cart.items.select_related('product', 'variant').all()

    subtotal = sum((item.line_total for item in items), start=Decimal('0.00'))

    # Coupon applied earlier in the session
    coupon = None
    coupon_discount = Decimal('0.00')
    coupon_error = None
    code = request.session.get('coupon_code')
    if code:
        coupon = Coupon.objects.filter(code=code, is_active=True).first()
        if coupon is None:
            request.session.pop('coupon_code', None)
            coupon_error = 'Your coupon is no longer valid.'
        else:
            ok, reason = coupon.is_valid_for(subtotal)
            if not ok:
                coupon_error = reason
                coupon_discount = Decimal('0.00')
            else:
                coupon_discount = coupon.discount_for(subtotal)

    from django.conf import settings

    discountable = subtotal - coupon_discount
    if discountable >= settings.FREE_SHIPPING_THRESHOLD or discountable == 0:
        shipping = Decimal('0.00')
    else:
        shipping = Decimal(settings.DEFAULT_SHIPPING_FEE)
    total = max(discountable, Decimal('0.00')) + shipping
    shipping_gap = max(Decimal('0.00'), Decimal(settings.FREE_SHIPPING_THRESHOLD) - discountable)

    context = {
        'cart': cart,
        'items': items,
        'subtotal': subtotal,
        'coupon': coupon,
        'coupon_discount': coupon_discount,
        'coupon_error': coupon_error,
        'shipping': shipping,
        'total': total,
        'shipping_gap': shipping_gap,
        'free_shipping_threshold': settings.FREE_SHIPPING_THRESHOLD,
        'shipping_needed': settings.DEFAULT_SHIPPING_FEE,
        'out_of_stock_items': [i for i in items if not i.is_available],
    }
    return render(request, 'cart/detail.html', context)


@login_required
@require_http_methods(['POST'])
def add_to_cart(request):
    product = get_object_or_404(Product, pk=request.POST.get('product_id'), is_active=True)
    size = request.POST.get('size', '').strip()
    color = request.POST.get('color', '').strip()
    try:
        quantity = max(1, int(request.POST.get('quantity', 1)))
    except (TypeError, ValueError):
        quantity = 1

    variant = None
    variants = product.variants.all()
    if variants.exists():
        # A variant product must have an explicit size + colour choice.
        if not size or not color:
            messages.error(request, 'Please choose a size and colour first.')
            return redirect(_safe_next(request) or product.get_absolute_url())
        variant = variants.filter(size=size, color__iexact=color).first()
        if variant is None:
            messages.error(request, 'That size and colour combination is not available.')
            return redirect(_safe_next(request) or product.get_absolute_url())
        available = variant.stock
    else:
        available = product.stock

    if available <= 0:
        messages.error(request, f'Sorry, "{product.name}" is out of stock.')
        return redirect(_safe_next(request) or product.get_absolute_url())

    cart = _get_cart(request)
    with transaction.atomic():
        item, created = CartItem.objects.get_or_create(
            cart=cart, product=product, variant=variant,
            defaults={'quantity': quantity},
        )
        if not created:
            new_qty = item.quantity + quantity
            if new_qty > available:
                messages.error(request, f'Only {available} left in stock for this selection.')
                new_qty = available
            item.quantity = new_qty
            item.save(update_fields=['quantity', 'updated_at'])

    label = product.name + (f' ({size} / {color})' if variant else '')
    messages.success(request, f'Added to cart: {label}.')
    if request.POST.get('buy_now'):
        return redirect('orders:checkout')
    return redirect(_safe_next(request) or 'cart:detail')


@login_required
@require_http_methods(['POST'])
def update_item(request, pk):
    cart = _get_cart(request)
    item = get_object_or_404(CartItem, pk=pk, cart=cart)
    try:
        quantity = int(request.POST.get('quantity', 1))
    except (TypeError, ValueError):
        quantity = item.quantity

    if quantity < 1:
        item.delete()
        messages.info(request, 'Item removed from your cart.')
        return redirect('cart:detail')

    available = item.available_stock
    if quantity > available:
        messages.error(request, f'Only {available} left in stock for "{item.product.name}".')
        quantity = available

    item.quantity = quantity
    item.save(update_fields=['quantity', 'updated_at'])
    messages.success(request, 'Cart updated.')
    return redirect('cart:detail')


@login_required
@require_http_methods(['POST'])
def remove_item(request, pk):
    cart = _get_cart(request)
    item = get_object_or_404(CartItem, pk=pk, cart=cart)
    name = item.product.name
    item.delete()
    messages.info(request, f'Removed "{name}" from your cart.')
    return redirect('cart:detail')


@login_required
@require_http_methods(['POST'])
def apply_coupon(request):
    cart = _get_cart(request)
    code = request.POST.get('code', '').strip().upper()
    if not code:
        messages.error(request, 'Enter a coupon code.')
        return redirect('cart:detail')

    coupon = Coupon.objects.filter(code=code, is_active=True).first()
    subtotal = cart.subtotal
    if coupon is None:
        messages.error(request, 'That coupon code does not exist.')
    else:
        ok, reason = coupon.is_valid_for(subtotal)
        if not ok:
            messages.error(request, reason)
        else:
            request.session['coupon_code'] = coupon.code
            messages.success(request, f'Coupon {coupon.code} applied — you save {coupon.discount_for(subtotal)}!')
            return redirect('cart:detail')
    return redirect('cart:detail')


@login_required
@require_http_methods(['POST'])
def remove_coupon(request):
    request.session.pop('coupon_code', None)
    messages.info(request, 'Coupon removed.')
    return redirect('cart:detail')
