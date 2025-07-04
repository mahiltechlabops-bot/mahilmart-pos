from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_view, name='home'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('order/', views.order_view, name='order'),
    path('products/', views.products_view, name='products'),
    path('sale_return/', views.sale_return_view, name='sale_return'),
    path('purchase/', views.purchase_view, name='purchase'),
    path('user/', views.user_view, name='user'),
]
