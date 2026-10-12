from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from catalog.models import Category, Product, ProductVariant

from .models import Cart, CartItem


class CartTestCase(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username='9111911191', phone='9111911191', password='pass1234')
        self.other = User.objects.create_user(username='9222922292', phone='9222922292', password='pass1234')
        self.client.force_login(self.user)

        category = Category.objects.create(name='Dresses')
        self.product = Product.objects.create(
            name='Veloura Signature Dress', category=category,
            description='Elegant signature dress', price=2000, discount_percent=10,
            stock=15,
        )
        self.variant = ProductVariant.objects.create(
            product=self.product, size='M', color='Lavender', stock=5,
        )
        self.product.stock = 15
        self.product.save()

    def add(self, **data):
        payload = {'product_id': self.product.pk, 'quantity': 1, 'size': 'M', 'color': 'Lavender'}
        payload.update(data)
        return self.client.post(reverse('cart:add'), payload)

    # -- adding ----------------------------------------------------------
    def test_add_variant_product_to_cart(self):
        response = self.add()
        self.assertRedirects(response, reverse('cart:detail'))
        item = CartItem.objects.get()
        self.assertEqual(item.variant, self.variant)
        self.assertEqual(item.quantity, 1)
        # Line total uses the discounted price from the database (2000 - 10%).
        self.assertEqual(str(item.line_total), '1800.00')

    def test_add_requires_size_and_color(self):
        response = self.add(size='', color='')
        self.assertRedirects(response, self.product.get_absolute_url())
        self.assertEqual(CartItem.objects.count(), 0)

    def test_add_rejects_invalid_color(self):
        response = self.add(color='Nonexistent')
        self.assertRedirects(response, self.product.get_absolute_url())
        self.assertEqual(CartItem.objects.count(), 0)

    def test_add_out_of_stock_is_rejected(self):
        self.variant.stock = 0
        self.variant.save()
        response = self.add()
        self.assertRedirects(response, self.product.get_absolute_url())
        self.assertEqual(CartItem.objects.count(), 0)

    def test_add_accumulates_quantity_up_to_stock(self):
        self.add()
        self.add()  # 2 in cart (stock = 5)
        self.add(quantity=10)  # capped at available stock
        item = CartItem.objects.get()
        self.assertEqual(item.quantity, 5)

    # -- quantity updates -------------------------------------------------
    def test_increase_quantity(self):
        self.add()
        item = CartItem.objects.get()
        self.client.post(reverse('cart:update', args=[item.pk]), {'quantity': 3})
        item.refresh_from_db()
        self.assertEqual(item.quantity, 3)

    def test_quantity_capped_at_stock(self):
        self.add()
        item = CartItem.objects.get()
        self.client.post(reverse('cart:update', args=[item.pk]), {'quantity': 99})
        item.refresh_from_db()
        self.assertEqual(item.quantity, self.variant.stock)

    def test_quantity_below_one_removes_item(self):
        self.add()
        item = CartItem.objects.get()
        self.client.post(reverse('cart:update', args=[item.pk]), {'quantity': 0})
        self.assertEqual(CartItem.objects.count(), 0)

    def test_remove_item(self):
        self.add()
        item = CartItem.objects.get()
        self.client.post(reverse('cart:remove', args=[item.pk]))
        self.assertEqual(CartItem.objects.count(), 0)

    # -- price integrity --------------------------------------------------
    def test_price_read_from_server_not_browser(self):
        """Changing a price in the database changes the cart total — the
        browser never dictates what an item costs."""
        self.add()
        item = CartItem.objects.get()
        self.product.price = 1000
        self.product.save()
        item.refresh_from_db()
        self.assertEqual(str(item.unit_price), '900.00')  # 1000 - 10%

    # -- ownership --------------------------------------------------------
    def test_users_cannot_touch_each_others_cart_items(self):
        self.add()
        item = CartItem.objects.get()
        self.client.force_login(self.other)
        response = self.client.post(reverse('cart:remove', args=[item.pk]))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(CartItem.objects.count(), 1)

    def test_cart_page_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse('cart:detail'))
        self.assertEqual(response.status_code, 302)

    def test_each_user_gets_own_cart(self):
        self.add()
        self.client.force_login(self.other)
        self.assertEqual(Cart.objects.filter(user=self.user).count(), 1)
        self.assertEqual(CartItem.objects.filter(cart__user=self.other).count(), 0)
