from .models import Cart
from wishlist.models import WishlistItem


def cart_summary(request):
    """Expose cart + wishlist counts to every template."""
    cart = None
    cart_items = 0
    wishlist_items = 0
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart_items = cart.item_count
        wishlist_items = WishlistItem.objects.filter(wishlist__user=request.user).count()
    return {
        'cart': cart,
        'cart_item_count': cart_items,
        'wishlist_item_count': wishlist_items,
    }
