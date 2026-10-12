from django import forms
from django.contrib.auth.password_validation import validate_password

from .models import Address, User, normalise_phone, phone_validator

BOOTSTRAP_CLASS = 'field'


class RegisterForm(forms.Form):
    """Create a new account with name, phone number and password."""

    name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'placeholder': 'Your full name', 'autofocus': True}),
    )
    phone = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={'placeholder': '10-digit phone number', 'inputmode': 'numeric'}),
    )
    password = forms.CharField(
        label='Password',
        strip=False,
        widget=forms.PasswordInput(attrs={'placeholder': 'At least 8 characters'}),
    )
    confirm_password = forms.CharField(
        label='Confirm password',
        strip=False,
        widget=forms.PasswordInput(attrs={'placeholder': 'Re-enter your password'}),
    )

    def clean_name(self):
        name = self.cleaned_data['name'].strip()
        if len(name) < 2:
            raise forms.ValidationError('Please enter your full name.')
        return name

    def clean_phone(self):
        phone = normalise_phone(self.cleaned_data['phone'])
        try:
            phone_validator(phone)
        except forms.ValidationError as exc:
            raise forms.ValidationError(exc.messages)
        if User.objects.filter(phone=phone).exists():
            raise forms.ValidationError('An account with this phone number already exists. Please sign in instead.')
        return phone

    def clean_password(self):
        password = self.cleaned_data['password']
        validate_password(password)
        return password

    def clean(self):
        cleaned = super().clean()
        password = cleaned.get('password')
        confirm = cleaned.get('confirm_password')
        if password and confirm and password != confirm:
            self.add_error('confirm_password', 'The two passwords do not match.')
        return cleaned

    def save(self, commit=True):
        name_parts = self.cleaned_data['name'].split(maxsplit=1)
        user = User(
            username=self.cleaned_data['phone'],  # username mirrors the unique phone number
            first_name=name_parts[0],
            last_name=name_parts[1] if len(name_parts) > 1 else '',
            phone=self.cleaned_data['phone'],
        )
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user


class LoginForm(forms.Form):
    """Sign in with phone number + password."""

    phone = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={'placeholder': 'Phone number', 'autofocus': True, 'inputmode': 'numeric'}),
    )
    password = forms.CharField(
        strip=False,
        widget=forms.PasswordInput(attrs={'placeholder': 'Password'}),
    )

    def clean_phone(self):
        phone = normalise_phone(self.cleaned_data['phone'])
        if not phone:
            raise forms.ValidationError('Please enter your phone number.')
        return phone


class ProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'placeholder': 'First name'}))
    last_name = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={'placeholder': 'Last name'}))
    email = forms.EmailField(required=False, widget=forms.EmailInput(attrs={'placeholder': 'Email (optional)'}))
    phone = forms.CharField(max_length=20, widget=forms.TextInput(attrs={'placeholder': 'Phone number'}))

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone']

    def clean_phone(self):
        phone = normalise_phone(self.cleaned_data['phone'])
        if User.objects.filter(phone=phone).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('Another account already uses this phone number.')
        return phone


class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = ['full_name', 'phone', 'line1', 'line2', 'city', 'state', 'pincode', 'is_default']
        widgets = {
            'full_name': forms.TextInput(attrs={'placeholder': 'Full name'}),
            'phone': forms.TextInput(attrs={'placeholder': 'Phone number'}),
            'line1': forms.TextInput(attrs={'placeholder': 'House no., street'}),
            'line2': forms.TextInput(attrs={'placeholder': 'Area, landmark (optional)'}),
            'city': forms.TextInput(attrs={'placeholder': 'City'}),
            'state': forms.TextInput(attrs={'placeholder': 'State'}),
            'pincode': forms.TextInput(attrs={'placeholder': '6-digit PIN code', 'inputmode': 'numeric'}),
        }

    def clean_phone(self):
        return normalise_phone(self.cleaned_data['phone'])
