from django import forms

from .models import Order


class CheckoutForm(forms.ModelForm):
    """Delivery details + payment choice for checkout."""

    payment_method = forms.ChoiceField(
        choices=[
            ('cod', 'Cash on Delivery'),
            ('demo', 'Demo Online Payment (no real charge)'),
        ],
        widget=forms.RadioSelect,
        initial='cod',
    )

    class Meta:
        model = Order
        fields = ['full_name', 'phone', 'address_line1', 'address_line2',
                  'city', 'state', 'pincode', 'customer_note', 'payment_method']
        widgets = {
            'full_name': forms.TextInput(attrs={'placeholder': 'Full name'}),
            'phone': forms.TextInput(attrs={'placeholder': 'Phone number', 'inputmode': 'numeric'}),
            'address_line1': forms.TextInput(attrs={'placeholder': 'House no., street'}),
            'address_line2': forms.TextInput(attrs={'placeholder': 'Area, landmark (optional)'}),
            'city': forms.TextInput(attrs={'placeholder': 'City'}),
            'state': forms.TextInput(attrs={'placeholder': 'State'}),
            'pincode': forms.TextInput(attrs={'placeholder': '6-digit PIN code', 'inputmode': 'numeric'}),
            'customer_note': forms.Textarea(attrs={
                'placeholder': 'Delivery instructions (optional)', 'rows': 2,
            }),
        }

    def clean_phone(self):
        from accounts.models import normalise_phone, phone_validator

        phone = normalise_phone(self.cleaned_data['phone'])
        try:
            phone_validator(phone)
        except forms.ValidationError as exc:
            raise forms.ValidationError(exc.messages)
        return phone

    def clean_pincode(self):
        pincode = self.cleaned_data['pincode'].strip()
        if not pincode.isdigit() or len(pincode) != 6:
            raise forms.ValidationError('Enter a valid 6-digit PIN code.')
        return pincode
