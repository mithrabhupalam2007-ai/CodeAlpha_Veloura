from django import forms

from .models import Category, ContactMessage, ProductReview, SIZE_CHOICES


class ProductFilterForm(forms.Form):
    """Server-side validated filters for the product listing pages."""

    q = forms.CharField(required=False, widget=forms.HiddenInput)
    category = forms.CharField(required=False, widget=forms.HiddenInput)
    min_price = forms.DecimalField(required=False, min_value=0, widget=forms.NumberInput(attrs={'placeholder': 'Min'}))
    max_price = forms.DecimalField(required=False, min_value=0, widget=forms.NumberInput(attrs={'placeholder': 'Max'}))
    color = forms.CharField(required=False, widget=forms.HiddenInput)
    size = forms.ChoiceField(required=False, choices=[('', 'Any size')] + SIZE_CHOICES)
    min_rating = forms.DecimalField(required=False, min_value=1, max_value=5,
                                    widget=forms.NumberInput(attrs={'placeholder': 'e.g. 4', 'step': '1', 'min': 1, 'max': 5}))
    availability = forms.ChoiceField(
        required=False,
        choices=[('', 'All'), ('in', 'In stock'), ('out', 'Out of stock')],
    )
    sort = forms.ChoiceField(
        required=False,
        choices=[
            ('newest', 'Newest arrivals'),
            ('popular', 'Popularity'),
            ('price_asc', 'Price: low to high'),
            ('price_desc', 'Price: high to low'),
            ('rating', 'Customer rating'),
        ],
    )

    def clean(self):
        cleaned = super().clean()
        low = cleaned.get('min_price')
        high = cleaned.get('max_price')
        if low is not None and high is not None and low > high:
            raise forms.ValidationError('Minimum price cannot be greater than maximum price.')
        return cleaned


class ReviewForm(forms.ModelForm):
    class Meta:
        model = ProductReview
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.Select(attrs={'class': 'input'}),
            'comment': forms.Textarea(attrs={
                'placeholder': 'Share fit, fabric and quality feedback…',
                'rows': 4,
            }),
        }


class NewsletterForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={'placeholder': 'Your email address'}))


class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ['name', 'email', 'subject', 'message']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Your name'}),
            'email': forms.EmailInput(attrs={'placeholder': 'Your email'}),
            'subject': forms.TextInput(attrs={'placeholder': 'How can we help?'}),
            'message': forms.Textarea(attrs={'placeholder': 'Write your message…', 'rows': 5}),
        }
