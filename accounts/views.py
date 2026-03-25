from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from .forms import CustomUserCreationForm
from shop.models import Orders

def signup_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)  # Use custom form
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('ShopHome')
    else:
        form = CustomUserCreationForm()  # Use custom form

    return render(request, 'accounts/signup.html', {'form': form})


def login_view(request):
    # (Keep your existing login_view code exactly the same)
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('ShopHome')
    else:
        form = AuthenticationForm()
    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    # (Keep your existing logout_view code exactly the same)
    if request.method == 'POST':
        logout(request)
        return redirect('ShopHome')

@login_required
def profile_view(request):
    # Fetch orders belonging to the logged-in user, newest first
    user_orders = Orders.objects.filter(user=request.user).order_by('-order_id')
    return render(request, 'accounts/profile.html', {'orders': user_orders})