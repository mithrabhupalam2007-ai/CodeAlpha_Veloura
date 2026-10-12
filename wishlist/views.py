from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from cart.models import Cart, CartItem
from catalog.models import Product

from .models import Wishlist, WishlistItem


def _get_wishlist(request):
    wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
    return wishlist


@login_required
def wishlist_page(request):
    wishlist = _get_wishlist(request)
    items = wishlist.items.select_related('product', 'product__category').all()
    return render(request, 'wishlist/list.html', {'items': items, 'wishlist': wishlist})


@login_required
@require_http_methods(['POST'])
def add_to_wishlist(request, product_id):
    product = get_object_or_404(Product, pk=product_id, is_active=True)
    wishlist = _get_wishlist(request)
    item, created = WishlistItem.objects.get_or_create(wishlist=wishlist, product=product)
    if created:
        messages.success(request, f'"{product.name}" saved to your wishlist.')
    else:
        messages.info(request, f'"{product.name}" is already in your wishlist.')
    return redirect(request.META.get('HTTP_REFERER', '/') or 'wishlist:list')


@login_required
@require_http_methods(['POST'])
def remove_from_wishlist(request, product_id):
    wishlist = _get_wishlist(request)
    item = WishlistItem.objects.filter(wishlist=wishlist, product_id=product_id).first()
    if item:
        name = item.product.name
        item.delete()
        messages.info(request, f'Removed "{name}" from your wishlist.')
    return redirect('wishlist:list')


@login_required
@require_http_methods(['POST'])
def move_to_cart(request, product_id):
    """Move a wishlist product into the cart (first in-stock variant)."""
    wishlist = _get_wishlist(request)
    item = get_object_or_404(WishlistItem, wishlist=wishlist, product_id=product_id)
    product = item.product

    if not product.is_in_stock:
        messages.error(request, f'Sorry, "{product.name}" is out of stock right now.')
        return redirect('wishlist:list')

    variant = product.variants.filter(stock__gt=0).first()
    cart, _ = Cart.objects.get_or_create(user=request.user)
    cart_item, created = CartItem.objects.get_or_create(
        cart=cart, product=product, variant=variant,
        defaults={'quantity': 1},
    )
    if not created:
        if cart_item.quantity < cart_item.available_stock:
            cart_item.quantity += 1
            cart_item.save(update_fields=['quantity', 'updated_at'])
        else:
            messages.warning(request, f'You already have the maximum available stock of "{product.name}" in your cart.')
            return redirect('wishlist:list')

    item.delete()
    messages.success(request, f'"{product.name}" moved to your cart.')
    return redirect('cart:detail')
