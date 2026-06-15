from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.middleware import SessionMiddleware
from shop.models import Orders
from accounts.views import profile_view

User = get_user_model()

class AccountsTestCase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='password123'
        )

    def test_user_creation(self):
        self.assertEqual(self.user.username, 'testuser')
        self.assertEqual(self.user.email, 'test@example.com')
        self.assertTrue(self.user.check_password('password123'))

    def test_profile_view_requires_login(self):
        request = self.factory.get(reverse('profile'))
        request.user = AnonymousUser()
        
        # Attach session middleware
        middleware = SessionMiddleware(lambda req: None)
        middleware.process_request(request)

        response = profile_view(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('two_factor:login'), response.url)

    def test_profile_view_authorized(self):
        # Create an order associated with user
        order = Orders.objects.create(
            name="Test User",
            email="test@example.com",
            address="123 Street",
            city="Cityville",
            state="Stateville",
            zip_code="12345",
            amount=500,
            user=self.user
        )

        request = self.factory.get(reverse('profile'))
        request.user = self.user
        
        # Attach session middleware
        middleware = SessionMiddleware(lambda req: None)
        middleware.process_request(request)

        response = profile_view(request)
        self.assertEqual(response.status_code, 200)
        # Verify rendered elements to bypass Python 3.14 template copy bugs
        self.assertContains(response, f"#{order.order_id}")
        self.assertContains(response, f"₹{order.amount}")
        self.assertContains(response, order.city)
