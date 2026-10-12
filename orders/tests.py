from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from cart.models import Cart, CartItem
from catalog.models import Category, Product, ProductVariant

from .models import Coupon, Order, OrderItem, Payment


def checkout_payload(**overrides):
    data = {
        'full_name': 'Test Customer',
        'phone': '9876543210',
        'address_line1': '12 Rose Villa',
        'address_line2': 'MG Road',
        'city': 'Pune',
        'state': 'Maharashtra',
        'pincode': '411001',
        'customer_note': '',
        'payment_method': 'cod',
    }
    data.update(overrides)
    return data


class OrderTestCase(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username='9333933393', phone='9333933393', password='pass1234')
        self.other = User.objects.create_user(username='9444944494', phone='9444944494', password='pass1234')
        self.client.force_login(self.user)

        category = Category.objects.create(name='Dresses')
        self.product = Product.objects.create(
            name='Order Test Dress', category=category,
            description='Dress for order tests', price=2000, discount_percent=0, stock=10,
        )
        self.variant = ProductVariant.objects.create(
            product=self.product, size='M', color='Lavender', stock=5,
        )

        self.cart = Cart.objects.create(user=self.user)
        self.item = CartItem.objects.create(
            cart=self.cart, product=self.product, variant=self.variant, quantity=2,
        )

    def place_order(self, **overrides):
        return self.client.post(reverse('orders:checkout'), checkout_payload(**overrides))

    # -- checkout ---------------------------------------------------------
    def test_checkout_creates_order_with_server_side_totals(self):
        response = self.place_order()
        order = Order.objects.get(user=self.user)
        self.assertRedirects(response, reverse('orders:detail', args=[order.order_number]))
        self.assertEqual(str(order.subtotal), '4000.00')       # 2 × 2000
        self.assertEqual(str(order.shipping_amount), '0.00')    # ≥ 1499 → free
        self.assertEqual(str(order.total), '4000.00')
        self.assertTrue(order.order_number.startswith('VL'))

    def test_checkout_stores_order_items_with_price_snapshot(self):
        self.place_order()
        item = OrderItem.objects.get()
        self.assertEqual(item.product_name, 'Order Test Dress')
        self.assertEqual(item.size, 'M')
        self.assertEqual(item.color, 'Lavender')
        self.assertEqual(str(item.unit_price), '2000.00')
        self.assertEqual(item.quantity, 2)

    def test_checkout_decrements_stock_and_increments_sales(self):
        self.place_order()
        self.variant.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(self.variant.stock, 3)   # 5 − 2
        self.assertEqual(self.product.stock, 8)   # 10 − 2
        self.assertEqual(self.product.sales_count, 2)

    def test_checkout_empties_cart_and_clears_coupon(self):
        session = self.client.session
        session['coupon_code'] = 'WELCOME10'
        session.save()
        self.place_order()
        self.assertEqual(CartItem.objects.count(), 0)
        self.assertNotIn('coupon_code', self.client.session)

    def test_cod_payment_record_is_pending_and_demo(self):
        self.place_order(payment_method='cod')
        payment = Payment.objects.get()
        self.assertEqual(payment.status, Payment.STATUS_PENDING)
        self.assertTrue(payment.is_demo)
        self.assertEqual(payment.method, 'cod')

    def test_demo_payment_record_created(self):
        self.place_order(payment_method='demo')
        payment = Payment.objects.get()
        self.assertEqual(payment.method, 'demo')
        self.assertTrue(payment.is_demo)
        # Demo payments never claim success without a provider confirmation.
        self.assertEqual(payment.status, Payment.STATUS_PENDING)

    def test_checkout_validates_stock_inside_transaction(self):
        """If stock vanished between cart and checkout, no order is created."""
        self.variant.stock = 1  # customer wants 2
        self.variant.save()
        self.place_order()
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(OrderItem.objects.count(), 0)
        # Stock untouched
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock, 1)

    def test_checkout_rejects_empty_cart(self):
        CartItem.objects.all().delete()
        response = self.client.get(reverse('orders:checkout'))
        self.assertRedirects(response, reverse('catalog:shop'))

    def test_checkout_form_rejects_bad_pincode(self):
        self.place_order(pincode='12')
        self.assertEqual(Order.objects.count(), 0)

    def test_price_manipulation_is_ignored(self):
        """Browser-submitted amounts cannot influence order totals."""
        self.place_order(total='1.00', subtotal='1.00', discount_amount='3999.00')
        order = Order.objects.get()
        self.assertEqual(str(order.total), '4000.00')
        self.assertEqual(str(order.discount_amount), '0.00')

    # -- coupons ----------------------------------------------------------
    def test_coupon_discount_applied_on_server(self):
        Coupon.objects.create(
            code='TEST20', discount_type='percent', value=20, min_order_amount=0,
        )
        session = self.client.session
        session['coupon_code'] = 'TEST20'
        session.save()
        self.place_order()
        order = Order.objects.get()
        self.assertEqual(str(order.discount_amount), '800.00')  # 20% of 4000
        self.assertEqual(str(order.total), '3200.00')
        # Free shipping still applies at 3200
        self.assertEqual(order.coupon.code, 'TEST20')

    def test_invalid_coupon_is_not_persisted(self):
        Coupon.objects.create(
            code='SMALL', discount_type='flat', value=100, min_order_amount=99999,
        )
        session = self.client.session
        session['coupon_code'] = 'SMALL'
        session.save()
        self.place_order()
        order = Order.objects.get()
        self.assertEqual(str(order.discount_amount), '0.00')
        self.assertIsNone(order.coupon)

    # -- ownership --------------------------------------------------------
    def test_users_cannot_view_each_others_orders(self):
        self.place_order()
        order = Order.objects.get()
        self.client.force_login(self.other)
        response = self.client.get(reverse('orders:detail', args=[order.order_number]))
        self.assertEqual(response.status_code, 404)

    def test_users_cannot_cancel_each_others_orders(self):
        self.place_order()
        order = Order.objects.get()
        self.client.force_login(self.other)
        response = self.client.post(reverse('orders:cancel', args=[order.order_number]))
        self.assertEqual(response.status_code, 404)
        order.refresh_from_db()
        self.assertNotEqual(order.status, Order.STATUS_CANCELLED)

    def test_order_history_only_shows_own_orders(self):
        self.place_order()
        self.client.force_login(self.other)
        self.place_order()
        orders = self.client.get(reverse('orders:history')).context['orders']
        self.assertEqual(list(orders), list(Order.objects.filter(user=self.other)))

    # -- cancellation -----------------------------------------------------
    def test_cancel_pending_order_restores_stock(self):
        self.place_order()
        order = Order.objects.get()
        response = self.client.post(reverse('orders:cancel', args=[order.order_number]))
        self.assertRedirects(response, reverse('orders:detail', args=[order.order_number]))

        order.refresh_from_db()
        self.variant.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_CANCELLED)
        self.assertEqual(self.variant.stock, 5)   # restored
        self.assertEqual(self.product.stock, 10)  # restored
        self.assertEqual(self.product.sales_count, 0)

    def test_cancelled_order_cannot_be_cancelled_twice(self):
        self.place_order()
        order = Order.objects.get()
        url = reverse('orders:cancel', args=[order.order_number])
        self.client.post(url)
        self.client.post(url)  # second attempt must not double-restore stock
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock, 5)

    def test_shipped_order_cannot_be_cancelled(self):
        self.place_order()
        order = Order.objects.get()
        order.status = Order.STATUS_SHIPPED
        order.save()
        self.client.post(reverse('orders:cancel', args=[order.order_number]))
        order.refresh_from_db()
        self.variant.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_SHIPPED)
        self.assertEqual(self.variant.stock, 3)   # untouched

    def test_order_status_step_property(self):
        order = Order(status=Order.STATUS_PROCESSING)
        self.assertEqual(order.status_step, 3)
        order.status = Order.STATUS_CANCELLED
        self.assertEqual(order.status_step, 0)


class CouponValidationTests(TestCase):
    def test_expired_coupon_rejected(self):
        from django.utils import timezone
        import datetime

        coupon = Coupon.objects.create(
            code='OLD', discount_type='flat', value=100,
            valid_from=timezone.now() - datetime.timedelta(days=10),
            valid_to=timezone.now() - datetime.timedelta(days=1),
        )
        ok, reason = coupon.is_valid_for(5000)
        self.assertFalse(ok)
        self.assertIn('expired', reason)

    def test_min_order_not_met(self):
        coupon = Coupon.objects.create(
            code='BIG', discount_type='percent', value=10, min_order_amount=5000,
        )
        ok, reason = coupon.is_valid_for(1000)
        self.assertFalse(ok)
        self.assertIn('minimum order', reason)

    def test_flat_discount_never_exceeds_subtotal(self):
        from decimal import Decimal

        coupon = Coupon.objects.create(
            code='HUGE', discount_type='flat', value=9999,
        )
        self.assertEqual(coupon.discount_for(Decimal('500.00')), Decimal('500.00'))
