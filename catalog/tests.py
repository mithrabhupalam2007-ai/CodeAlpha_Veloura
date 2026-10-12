from django.test import TestCase
from django.urls import reverse

from .models import Category, Product, ProductReview


def make_product(name, category, price=1000, discount=0, stock=10, **kwargs):
    return Product.objects.create(
        name=name, category=category, description=f'{name} description silk dress top',
        price=price, discount_percent=discount, stock=stock, **kwargs,
    )


class CatalogFixtureMixin:
    @classmethod
    def setUpTestData(cls):
        cls.dresses = Category.objects.create(name='Dresses')
        cls.tops = Category.objects.create(name='Tops and T-shirts')
        cls.p1 = make_product('Lavender Party Gown', cls.dresses, price=2000, discount=20, sales_count=50)
        cls.p2 = make_product('Casual Cotton Top', cls.tops, price=500, discount=0, sales_count=10)
        cls.p3 = make_product('Silk Evening Dress', cls.dresses, price=3000, discount=0, sales_count=5, stock=0)

    def login(self):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user, _ = User.objects.get_or_create(
            username='7777777777',
            defaults={'phone': '7777777777'},
        )
        if not user.has_usable_password():
            user.set_password('pass1234')
            user.save(update_fields=['password'])
        self.client.force_login(user)
        return user


class SearchAndFilterTests(CatalogFixtureMixin, TestCase):
    def setUp(self):
        self.login()

    def test_search_by_product_name(self):
        response = self.client.get(reverse('catalog:search'), {'q': 'Party Gown'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Lavender Party Gown')
        self.assertNotContains(response, 'Casual Cotton Top')

    def test_search_by_category_name(self):
        response = self.client.get(reverse('catalog:search'), {'q': 'Dresses'})
        self.assertContains(response, 'Lavender Party Gown')
        self.assertContains(response, 'Silk Evening Dress')

    def test_filter_by_price_range(self):
        response = self.client.get(reverse('catalog:shop'), {'min_price': 400, 'max_price': 600})
        self.assertContains(response, 'Casual Cotton Top')
        self.assertNotContains(response, 'Lavender Party Gown')

    def test_filter_rejects_inverted_price_range(self):
        response = self.client.get(reverse('catalog:shop'), {'min_price': 900, 'max_price': 100})
        self.assertEqual(response.status_code, 200)
        # The form refuses the invalid range rather than silently returning all.
        self.assertContains(response, 'Minimum price cannot be greater')

    def test_filter_by_availability_in_stock(self):
        response = self.client.get(reverse('catalog:shop'), {'availability': 'in'})
        self.assertContains(response, 'Lavender Party Gown')
        self.assertNotContains(response, 'Silk Evening Dress')

    def test_sort_price_ascending(self):
        response = self.client.get(reverse('catalog:shop'), {'sort': 'price_asc'})
        products = list(response.context['products'])
        self.assertEqual(products[0].pk, self.p2.pk)

    def test_sort_price_descending(self):
        response = self.client.get(reverse('catalog:shop'), {'sort': 'price_desc'})
        products = list(response.context['products'])
        self.assertEqual(products[0].pk, self.p3.pk)

    def test_sort_by_popularity(self):
        response = self.client.get(reverse('catalog:shop'), {'sort': 'popular'})
        products = list(response.context['products'])
        self.assertEqual(products[0].pk, self.p1.pk)

    def test_discounted_price_math(self):
        self.assertEqual(str(self.p1.discounted_price), '1600.00')
        self.assertEqual(str(self.p1.discount_amount), '400.00')
        self.assertEqual(str(self.p2.discounted_price), '500.00')


class ProductDetailTests(CatalogFixtureMixin, TestCase):
    def setUp(self):
        self.login()

    def test_detail_page_renders(self):
        response = self.client.get(self.p1.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Lavender Party Gown')
        self.assertContains(response, '₹1600.00')

    def test_detail_404_for_missing_product(self):
        response = self.client.get('/product/does-not-exist/')
        self.assertEqual(response.status_code, 404)

    def test_review_requires_login(self):
        self.client.logout()
        response = self.client.post(
            reverse('catalog:submit_review', args=[self.p1.slug]),
            {'rating': 5, 'comment': 'Lovely!'},
        )
        self.assertEqual(response.status_code, 302)

    def test_review_saved_for_logged_in_user(self):
        user = self.login()
        self.client.post(
            reverse('catalog:submit_review', args=[self.p1.slug]),
            {'rating': 4, 'comment': 'Great fit'},
        )
        review = ProductReview.objects.get(product=self.p1, user=user)
        self.assertEqual(review.rating, 4)

    def test_review_updates_existing_review(self):
        user = self.login()
        url = reverse('catalog:submit_review', args=[self.p1.slug])
        self.client.post(url, {'rating': 3, 'comment': 'First'})
        self.client.post(url, {'rating': 5, 'comment': 'Changed my mind'})
        self.assertEqual(ProductReview.objects.filter(product=self.p1, user=user).count(), 1)
        self.assertEqual(ProductReview.objects.get(product=self.p1, user=user).rating, 5)

    def test_home_sections_show_products(self):
        response = self.client.get(reverse('catalog:home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Lavender Party Gown')
        self.assertContains(response, 'Shop by Category')
