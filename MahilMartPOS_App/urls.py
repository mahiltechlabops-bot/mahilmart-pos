from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.login_view, name='home'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('billing/', views.create_invoice_view, name='billing'),
    path('order/', views.order_view, name='order'),
    path('products/', views.products_view, name='products'),
    path('item/create', views.item_creation, name='items'),
    path('barcode',views.Item_barcode,name='item_barcode'),
    path('unit', views.Unit_creation, name='unit_creation'),
    path('group', views.Group_creation, name='group_creation'),
    path('brand', views.Brand_creation, name='brand_creation'),
    path('sale_return/', views.sale_return_view, name='sale_return'),
    path('purchase/', views.purchase_view, name='purchase'),
    path('api/item/fetch/', views.fetch_item, name='fetch_item'),
    path('api/purchase/create/', views.create_purchase, name='create_purchase'),
    path('purchase_return/', views.purchase_return_view, name='purchase_return'),
    path('stock_adjustment/', views.stock_adjustment_view, name='stock_adjustment'),
    path('inventory/', views.inventory_view, name='inventory'),
    path('product/<int:pk>/', views.product_detail, name='product_detail'), 
    path('suppliers/', views.suppliers_view, name='suppliers'),
    path('suppliers/add/', views.add_supplier, name='add_supplier'),
    path('customers/', views.customers_view, name='customers'),
    path('add-customer/', views.add_customer, name='add_customer'),
    path('submit-customer/', views.submit_customer, name='submit_customer'),
    path('user/', views.user_view, name='user'),
    path('company/', views.company_settings_view, name='company_details'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
]