from django.urls import path

from . import views

app_name = 'catalog'

urlpatterns = [
    path('', views.home, name='home'),
    path('shop/', views.shop, name='shop'),
    path('search/', views.search, name='search'),
    path('new-arrivals/', views.new_arrivals, name='new_arrivals'),
    path('trending/', views.trending, name='trending'),
    path('category/<slug:slug>/', views.category_listing, name='category'),
    path('product/<slug:slug>/', views.product_detail, name='product_detail'),
    path('product/<slug:slug>/review/', views.submit_review, name='submit_review'),
    path('newsletter/', views.newsletter_subscribe, name='newsletter'),
    path('contact/', views.contact, name='contact'),
    path('page/<slug:slug>/', views.static_page, name='page'),
]
