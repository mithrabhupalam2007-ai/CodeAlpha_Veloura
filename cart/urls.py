from django.urls import path

from . import views

app_name = 'cart'

urlpatterns = [
    path('', views.cart_detail, name='detail'),
    path('add/', views.add_to_cart, name='add'),
    path('item/<int:pk>/update/', views.update_item, name='update'),
    path('item/<int:pk>/remove/', views.remove_item, name='remove'),
    path('coupon/apply/', views.apply_coupon, name='apply_coupon'),
    path('coupon/remove/', views.remove_coupon, name='remove_coupon'),
]
