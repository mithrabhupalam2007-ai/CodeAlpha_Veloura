from django.conf import settings
from django.db import models

from catalog.models import Product


class Wishlist(models.Model):
    """A customer's saved products. One wishlist per user."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wishlist')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Wishlist of {self.user}'


class WishlistItem(models.Model):
    wishlist = models.ForeignKey(Wishlist, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='wishlist_items')
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-added_at']
        constraints = [
            models.UniqueConstraint(fields=['wishlist', 'product'], name='unique_product_in_wishlist'),
        ]

    def __str__(self):
        return f'{self.product.name} in {self.wishlist.user} wishlist'
