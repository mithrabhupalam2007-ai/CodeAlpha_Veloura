from django.urls import path

from . import views

app_name = 'accounts'

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('addresses/<int:pk>/delete/', views.address_delete, name='address_delete'),
    path('settings/', views.settings_view, name='settings'),
    path('coupons/', views.coupons, name='coupons'),
    path('payments/', views.payments, name='payments'),
]
