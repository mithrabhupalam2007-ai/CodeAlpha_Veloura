from django.urls import path

from . import views

app_name = 'orders'

urlpatterns = [
    path('checkout/', views.checkout, name='checkout'),
    path('history/', views.order_history, name='history'),
    path('<str:order_number>/', views.order_detail, name='detail'),
    path('<str:order_number>/cancel/', views.cancel_order, name='cancel'),
]
