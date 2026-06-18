import random
import time
from django.shortcuts import render, redirect
from django.core.paginator import Paginator
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from .forms import CustomUserCreationForm
from .models import CustomUser
from shop.models import Orders
from accounts.tasks import send_async_email


def signup_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False  # Account inactive until email verified
            user.save()

            # Generate 6-digit OTP and store it in session with 5-minute expiry
            otp = f"{random.randint(100000, 999999)}"
            request.session['verification_otp'] = otp
            request.session['verification_user_id'] = user.id
            request.session['verification_expiry'] = time.time() + 300  # 5 minutes

            subject = 'Verify your MyAwesomeCart account'
            message = (
                f"Hi {user.username},\n\n"
                f"Thank you for registering. Your 6-digit verification code is:\n\n"
                f"OTP: {otp}\n\n"
                f"This code will expire in 5 minutes. If you did not register, please ignore this email.\n\n"
                f"— MyAwesomeCart Team"
            )
            send_async_email.delay(subject, message, [user.email])

            return redirect('verify_code')
    else:
        form = CustomUserCreationForm()

    return render(request, 'accounts/signup.html', {'form': form})


def verify_code(request):
    """Verify the 6-digit OTP code submitted by the user."""
    if request.method == 'POST':
        submitted_code = request.POST.get('code', '').strip()
        otp = request.session.get('verification_otp')
        user_id = request.session.get('verification_user_id')
        expiry = request.session.get('verification_expiry', 0)

        if not otp or not user_id:
            messages.error(request, 'Session expired or invalid. Please sign up again.')
            return redirect('signup')

        if time.time() > expiry:
            # Clean session keys
            request.session.pop('verification_otp', None)
            request.session.pop('verification_user_id', None)
            request.session.pop('verification_expiry', None)
            messages.error(request, 'The verification code has expired. Please sign up again.')
            return redirect('signup')

        if submitted_code == otp:
            try:
                user = CustomUser.objects.get(pk=user_id)
                user.is_active = True
                user.save()
                # Explicitly specify the backend since multiple backends are configured
                user.backend = 'django.contrib.auth.backends.ModelBackend'
                login(request, user)

                # Clean session keys
                request.session.pop('verification_otp', None)
                request.session.pop('verification_user_id', None)
                request.session.pop('verification_expiry', None)

                messages.success(request, 'Your account has been activated! Welcome to MyAwesomeCart.')
                return redirect('profile')
            except CustomUser.DoesNotExist:
                messages.error(request, 'User not found. Please sign up again.')
                return redirect('signup')
        else:
            messages.error(request, 'Invalid verification code. Please check and try again.')
            return render(request, 'accounts/verify_code.html', {'code_entered': submitted_code})

    return render(request, 'accounts/verify_code.html')


def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('ShopHome')
        else:
            messages.error(request, 'Invalid credentials.')
    else:
        form = AuthenticationForm()
    return render(request, 'accounts/login.html', {'form': form})


@require_POST
def logout_view(request):
    logout(request)
    return redirect('ShopHome')


@login_required
def profile_view(request):
    # Fetch orders belonging to the logged-in user, newest first
    user_orders = Orders.objects.filter(user=request.user).order_by('-order_id')
    paginator = Paginator(user_orders, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'accounts/profile.html', {'page_obj': page_obj})