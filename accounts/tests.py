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

    def test_signup_generates_otp_in_session(self):
        from accounts.views import signup_view
        
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'phone_number': '1234567890',
            'address': '123 Test St',
            'password': 'password123',
            'password1': 'password123',
            'password2': 'password123',
        }
        request = self.factory.post(reverse('signup'), data=data)
        request.user = AnonymousUser()
        
        middleware = SessionMiddleware(lambda req: None)
        middleware.process_request(request)
        
        response = signup_view(request)
        
        # Should redirect to verify_code
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('verify_code'))
        
        # Verify OTP is stored in session
        self.assertIn('verification_otp', request.session)
        self.assertIn('verification_user_id', request.session)
        self.assertIn('verification_expiry', request.session)
        self.assertEqual(len(request.session['verification_otp']), 6)
        self.assertTrue(request.session['verification_otp'].isdigit())

    def test_verify_code_correct_otp(self):
        from accounts.views import verify_code
        import time
        
        # Create an inactive user manually representing signup state
        inactive_user = User.objects.create_user(
            username='inactiveuser',
            email='inactive@example.com',
            password='password123',
            is_active=False
        )
        
        # Setup session for verify_code
        request = self.factory.post(reverse('verify_code'), data={'code': '123456'})
        request.user = AnonymousUser()
        
        middleware = SessionMiddleware(lambda req: None)
        middleware.process_request(request)
        
        request.session['verification_otp'] = '123456'
        request.session['verification_user_id'] = inactive_user.id
        request.session['verification_expiry'] = time.time() + 300 # valid
        
        from django.contrib.messages.storage.fallback import FallbackStorage
        setattr(request, '_messages', FallbackStorage(request))
        
        response = verify_code(request)
        
        # Should redirect to profile on success
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('profile'))
        
        # Verify user is active now
        inactive_user.refresh_from_db()
        self.assertTrue(inactive_user.is_active)
        
        # Verify session keys cleared
        self.assertNotIn('verification_otp', request.session)
        self.assertNotIn('verification_user_id', request.session)

    def test_verify_code_incorrect_otp(self):
        from accounts.views import verify_code
        import time
        
        inactive_user = User.objects.create_user(
            username='inactiveuser2',
            email='inactive2@example.com',
            password='password123',
            is_active=False
        )
        
        request = self.factory.post(reverse('verify_code'), data={'code': '111111'})
        request.user = AnonymousUser()
        
        middleware = SessionMiddleware(lambda req: None)
        middleware.process_request(request)
        
        request.session['verification_otp'] = '123456'
        request.session['verification_user_id'] = inactive_user.id
        request.session['verification_expiry'] = time.time() + 300
        
        from django.contrib.messages.storage.fallback import FallbackStorage
        setattr(request, '_messages', FallbackStorage(request))
        
        response = verify_code(request)
        
        # Should return 200 (render the template with error message)
        self.assertEqual(response.status_code, 200)
        
        # Verify user remains inactive
        inactive_user.refresh_from_db()
        self.assertFalse(inactive_user.is_active)

    def test_verify_code_expired_otp(self):
        from accounts.views import verify_code
        import time
        
        inactive_user = User.objects.create_user(
            username='inactiveuser3',
            email='inactive3@example.com',
            password='password123',
            is_active=False
        )
        
        request = self.factory.post(reverse('verify_code'), data={'code': '123456'})
        request.user = AnonymousUser()
        
        middleware = SessionMiddleware(lambda req: None)
        middleware.process_request(request)
        
        request.session['verification_otp'] = '123456'
        request.session['verification_user_id'] = inactive_user.id
        request.session['verification_expiry'] = time.time() - 10 # expired 10s ago
        
        from django.contrib.messages.storage.fallback import FallbackStorage
        setattr(request, '_messages', FallbackStorage(request))
        
        response = verify_code(request)
        
        # Should redirect to signup view on expiry
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('signup'))
        
        # Verify user remains inactive
        inactive_user.refresh_from_db()
        self.assertFalse(inactive_user.is_active)
        
        # Verify session keys cleared
        self.assertNotIn('verification_otp', request.session)
