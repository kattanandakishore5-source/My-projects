from django.shortcuts import render, redirect
from django.core.paginator import Paginator
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.contrib import messages
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
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

            # Generate verification token and send email
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            current_site = get_current_site(request)
            protocol = 'https' if request.is_secure() else 'http'
            activation_link = f"{protocol}://{current_site.domain}/activate/{uid}/{token}/"

            subject = 'Activate your MyAwesomeCart account'
            message = (
                f"Hi {user.username},\n\n"
                f"Thank you for registering. Please click the link below to activate your account:\n\n"
                f"{activation_link}\n\n"
                f"If you did not register, please ignore this email.\n\n"
                f"— MyAwesomeCart Team"
            )
            send_async_email.delay(subject, message, [user.email])

            return render(request, 'accounts/signup_done.html', {'email': user.email})
    else:
        form = CustomUserCreationForm()

    return render(request, 'accounts/signup.html', {'form': form})


def activate_account(request, uidb64, token):
    """Activate a user account via the email verification link."""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = CustomUser.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        messages.success(request, 'Your account has been activated! You can now log in.')
        return redirect('login')
    else:
        messages.error(request, 'The activation link is invalid or has expired.')
        return redirect('signup')


def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
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