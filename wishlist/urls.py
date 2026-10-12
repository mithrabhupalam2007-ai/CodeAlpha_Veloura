from django.urls import path

from . import views

app_name = 'wishlist'

urlpatterns = [
    path('', views.wishlist_page, name='list'),
    path('add/<int:product_id>/', views.add_to_wishlist, name='add'),
    path('remove/<int:product_id>/', views.remove_from_wishlist, name='remove'),
    path('move/<int:product_id>/', views.move_to_cart, name='move'),
]
