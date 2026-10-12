from django.test import TestCase
from django.urls import reverse

from .models import User


class RegisterTests(TestCase):
    def test_register_creates_account_with_hashed_password(self):
        response = self.client.post(reverse('accounts:register'), {
            'name': 'Test Person',
            'phone': '9876543210',
            'password': 'Str0ngPass!23',
            'confirm_password': 'Str0ngPass!23',
        })
        self.assertRedirects(response, reverse('accounts:login'))
        user = User.objects.get(phone='9876543210')
        self.assertEqual(user.first_name, 'Test')
        self.assertTrue(user.check_password('Str0ngPass!23'))
        # Password must be hashed, never stored in plain text.
        self.assertNotIn('Str0ngPass!23', user.password)
        self.assertTrue(user.password.startswith(('pbkdf2_', 'argon2', 'bcrypt')))

    def test_register_rejects_duplicate_phone(self):
        User.objects.create_user(username='1111111111', phone='1111111111', password='x')
        response = self.client.post(reverse('accounts:register'), {
            'name': 'Dup User',
            'phone': '1111111111',
            'password': 'Str0ngPass!23',
            'confirm_password': 'Str0ngPass!23',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'already exists')
        self.assertEqual(User.objects.filter(phone='1111111111').count(), 1)

    def test_register_rejects_invalid_phone(self):
        response = self.client.post(reverse('accounts:register'), {
            'name': 'Bad Phone',
            'phone': 'abc',
            'password': 'Str0ngPass!23',
            'confirm_password': 'Str0ngPass!23',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'valid phone number')
        self.assertFalse(User.objects.filter(phone='abc').exists())

    def test_register_rejects_mismatched_passwords(self):
        response = self.client.post(reverse('accounts:register'), {
            'name': 'Mismatch',
            'phone': '9876500000',
            'password': 'Str0ngPass!23',
            'confirm_password': 'Different!45',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'do not match')


class LoginTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='9999999999', phone='9999999999', password='Secret123!',
        )

    def test_login_with_phone_and_password(self):
        response = self.client.post(reverse('accounts:login'), {
            'phone': '9999999999', 'password': 'Secret123!',
        })
        self.assertRedirects(response, reverse('catalog:home'))

    def test_login_with_wrong_password_fails(self):
        response = self.client.post(reverse('accounts:login'), {
            'phone': '9999999999', 'password': 'wrong',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Incorrect password')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_login_with_unknown_phone_fails(self):
        response = self.client.post(reverse('accounts:login'), {
            'phone': '9000000000', 'password': 'Secret123!',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No account found')

    def test_logout_requires_post(self):
        self.client.login(username='9999999999', password='Secret123!')
        response = self.client.get(reverse('accounts:logout'))
        self.assertEqual(response.status_code, 405)

    def test_logout_post_signs_out(self):
        self.client.login(username='9999999999', password='Secret123!')
        response = self.client.post(reverse('accounts:logout'))
        self.assertRedirects(response, reverse('accounts:login'))
        self.assertNotIn('_auth_user_id', self.client.session)


class AccessControlTests(TestCase):
    """Guests must sign in before browsing; users only see their own data."""

    def test_home_requires_login(self):
        response = self.client.get(reverse('catalog:home'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('accounts:login'), response.url)

    def test_shop_requires_login(self):
        response = self.client.get(reverse('catalog:shop'))
        self.assertEqual(response.status_code, 302)

    def test_checkout_requires_login(self):
        response = self.client.get(reverse('orders:checkout'))
        self.assertEqual(response.status_code, 302)

    def test_order_history_requires_login(self):
        response = self.client.get(reverse('orders:history'))
        self.assertEqual(response.status_code, 302)

    def test_login_redirects_authenticated_user_to_home(self):
        User.objects.create_user(username='8888888888', phone='8888888888', password='x')
        self.client.login(username='8888888888', password='x')
        response = self.client.get(reverse('accounts:login'))
        self.assertRedirects(response, reverse('catalog:home'))
