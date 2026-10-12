from decimal import Decimal

from django.conf import settings
from django.db import models

from catalog.models import Product, ProductVariant


class Cart(models.Model):
    """A customer's shopping cart. One cart per user."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Cart of {self.user}'

    @property
    def item_count(self):
        return sum(item.quantity for item in self.items.all())

    @property
    def subtotal(self):
        """Server-computed subtotal — never trust browser prices."""
        return sum((item.line_total for item in self.items.all()), start=Decimal('0.00'))


class CartItem(models.Model):
    """One product/variant line inside a cart."""

    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='cart_items')
    variant = models.ForeignKey(
        ProductVariant, on_delete=models.CASCADE, related_name='cart_items',
        null=True, blank=True, help_text='Null for products without size/colour variants',
    )
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['added_at']
        constraints = [
            models.UniqueConstraint(fields=['cart', 'variant'], name='unique_variant_in_cart'),
        ]

    def __str__(self):
        variant_label = f' ({self.variant})' if self.variant else ''
        return f'{self.quantity} × {self.product.name}{variant_label}'

    @property
    def unit_price(self):
        """Current selling price, read from the database at render time."""
        return self.product.discounted_price

    @property
    def line_total(self):
        return (self.unit_price * Decimal(self.quantity)).quantize(Decimal('0.01'))

    @property
    def size(self):
        return self.variant.size if self.variant else ''

    @property
    def color(self):
        return self.variant.color if self.variant else ''

    @property
    def available_stock(self):
        """Max quantity the customer may have of this line."""
        if self.variant_id:
            return self.variant.stock
        return self.product.stock

    @property
    def is_available(self):
        return self.available_stock > 0
