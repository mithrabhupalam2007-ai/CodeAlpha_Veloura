from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from orders.models import Coupon, Payment

from .forms import AddressForm, LoginForm, ProfileForm, RegisterForm
from .models import Address, User


def _redirect_after_auth(request):
    next_url = request.GET.get('next') or request.POST.get('next')
    if next_url and next_url.startswith('/') and not next_url.startswith('//'):
        return redirect(next_url)
    return redirect('catalog:home')


@require_http_methods(['GET', 'POST'])
def register(request):
    if request.user.is_authenticated:
        return redirect('catalog:home')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            auth_user = form.save()
            messages.success(request, f'Welcome, {auth_user.full_name}! Your account has been created. Please sign in.')
            return redirect('accounts:login')
        messages.error(request, 'Please correct the errors below.')
    else:
        form = RegisterForm()
    return render(request, 'accounts/register.html', {'form': form})


@require_http_methods(['GET', 'POST'])
def login_view(request):
    if request.user.is_authenticated:
        return redirect('catalog:home')
    form = LoginForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        phone = form.cleaned_data['phone']
        password = form.cleaned_data['password']
        user = User.objects.filter(phone=phone).first()
        if user is None:
            messages.error(request, 'No account found with this phone number.')
        else:
            auth_user = authenticate(request, username=user.username, password=password)
            if auth_user is None:
                messages.error(request, 'Incorrect password. Please try again.')
            else:
                login(request, auth_user)
                messages.success(request, f'Signed in as {auth_user.full_name}.')
                return _redirect_after_auth(request)
    return render(request, 'accounts/login.html', {'form': form, 'next': request.GET.get('next', '')})


@require_http_methods(['POST'])
def logout_view(request):
    logout(request)
    messages.info(request, 'You have been signed out.')
    return redirect('accounts:login')


@login_required
@require_http_methods(['GET', 'POST'])
def profile(request):
    """Manage account: profile details + saved addresses."""
    if request.method == 'POST':
        action = request.POST.get('action')
        form = ProfileForm(instance=request.user)  # default if the address branch runs
        if action == 'profile':
            form = ProfileForm(request.POST, instance=request.user)
            if form.is_valid():
                form.save()
                messages.success(request, 'Profile updated successfully.')
                return redirect('accounts:profile')
            messages.error(request, 'Please correct the errors below.')
        elif action == 'address':
            address_form = AddressForm(request.POST)
            if address_form.is_valid():
                address = address_form.save(commit=False)
                address.user = request.user
                address.save()
                messages.success(request, 'Address added.')
                return redirect('accounts:profile')
            messages.error(request, 'Please correct the address errors.')
    else:
        form = ProfileForm(instance=request.user)

    addresses = request.user.addresses.all()
    if 'address_form' not in locals():
        address_form = AddressForm()
    return render(request, 'accounts/profile.html', {
        'form': form,
        'address_form': address_form,
        'addresses': addresses,
    })


@login_required
@require_http_methods(['POST'])
def address_delete(request, pk):
    address = Address.objects.filter(pk=pk, user=request.user).first()
    if address is None:
        messages.error(request, 'Address not found.')
        return redirect('accounts:profile')
    address.delete()
    messages.success(request, 'Address removed.')
    return redirect('accounts:profile')


@login_required
@require_http_methods(['GET', 'POST'])
def settings_view(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Password changed successfully.')
            return redirect('accounts:settings')
        messages.error(request, 'Please correct the errors below.')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'accounts/settings.html', {'form': form})


@login_required
def coupons(request):
    from django.db.models import Q
    from django.utils import timezone

    now = timezone.now()
    active = Coupon.objects.filter(
        is_active=True,
        valid_from__lte=now,
    ).filter(Q(valid_to__isnull=True) | Q(valid_to__gte=now))
    return render(request, 'accounts/coupons.html', {'coupons': active})


@login_required
def payments(request):
    records = Payment.objects.filter(order__user=request.user).select_related('order')
    return render(request, 'accounts/payments.html', {'records': records})
