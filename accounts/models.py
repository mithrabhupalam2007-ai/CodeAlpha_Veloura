from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models

phone_validator = RegexValidator(
    regex=r'^\+?[0-9]{10,15}$',
    message='Enter a valid phone number: 10 to 15 digits, optionally starting with +.',
)


def normalise_phone(raw: str) -> str:
    """Strip spaces, dashes, parentheses and dots from a phone number."""
    return ''.join(ch for ch in raw.strip() if ch.isdigit() or ch == '+')


class User(AbstractUser):
    """Veloura customer. The phone number is the unique sign-in identifier."""

    phone = models.CharField(
        max_length=20,
        unique=True,
        validators=[phone_validator],
        help_text='Used to sign in. 10-15 digits, optionally starting with +.',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    REQUIRED_FIELDS = ['phone']

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        name = self.get_full_name() or self.username
        return f'{name} ({self.phone})'

    @property
    def full_name(self):
        return self.get_full_name() or self.username

    def clean(self):
        super().clean()
        self.phone = normalise_phone(self.phone)


class Address(models.Model):
    """A saved delivery address belonging to a customer."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    full_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=20, validators=[phone_validator])
    line1 = models.CharField(max_length=255, help_text='House / street')
    line2 = models.CharField(max_length=255, blank=True, help_text='Area / landmark')
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10, validators=[RegexValidator(r'^[0-9]{6}$', 'Enter a valid 6-digit PIN code.')])
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_default', '-updated_at']

    def __str__(self):
        return f'{self.full_name}, {self.city} - {self.pincode}'

    @property
    def single_line(self):
        parts = [self.line1, self.line2, self.city, self.state, self.pincode]
        return ', '.join(p for p in parts if p)

    def save(self, *args, **kwargs):
        if self.is_default:
            Address.objects.filter(user=self.user, is_default=True).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)
