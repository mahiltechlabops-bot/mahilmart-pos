from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from django.conf.urls import handler403

urlpatterns = [
    # login page
    path('', views.login_view, name='home'),

    # dashboard page
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('generate-report/', views.generate_report, name='generate_report'),
    path('billing/<int:id>/', views.billing_detail_view, name='billing_detail'),
    path('billing/<int:bill_id>/items/', views.billing_items_api, name='billing_items_api'),
    path('sales-chart-data/', views.sales_chart_data, name='sales_chart_data'),

    # billing page
    path('billing/', views.create_invoice_view, name='billing'),
    path('ajax/get-item-info/', views.get_item_info, name='get_item_info'),
    path("ajax/get-itemname-info/", views.get_itemname_info, name="get_itemname_info"), 

    # config page
    path('add/', views.add_billtype, name='add'),


    path('order-payments/<int:order_id>/', views.order_payments, name='order_payments'),

    # order page
    path('order/', views.order_view, name='order'),
    path('orders/', views.order_list, name='order_list'),
    path('order-success/', views.order_success, name='order_success'),
    path('orders/<int:order_id>/', views.order_detail, name='order_detail'),

    # create new order (Not used)
    path('new-order/', views.create_order, name='create_order'),
    path('orders/<int:order_id>/edit/', views.edit_order, name='edit_order'),

    # quotation page
    path('quotation/save/', views.create_quotation, name='create_quotation'),
    path('quotation/detail/<str:qtn_no>/', views.quotation_detail, name='quotation_detail'),    
    path('quotation/last/', views.get_last_quotation, name='last_quotation'),
    path('update-payment/<int:order_id>/', views.update_payment, name='update_payment'),
    path('convert-to-order/<str:qtn_no>/', views.convert_quotation_to_order, name='convert_to_order'),

    # sale return page
    path('sale-return/', views.sale_return_view, name='sale_return'),
    path('sale-return/success/', views.sale_return_success_view, name='sale_return_success'),
    path('sale_return/detail/<int:pk>/', views.sale_return_detail, name='sale_return_detail'),
    path('sale-return-items/', views.sale_return_items_api, name='sale_return_items_api'),

    # product page
    path('products/', views.products_view, name='products'),

    # item page
    path('item/create', views.item_creation, name='items'),
    path('unit', views.Unit_creation, name='unit_creation'),
    path('group', views.Group_creation, name='group_creation'),
    path('brand', views.Brand_creation, name='brand_creation'),
    path('tax', views.Tax_creation, name='tax_creation'),    
    path('items/', views.items_list, name='items_list'),
    path('items/delete/<int:item_id>/', views.delete_item, name='delete_item'),   
    path("check-item-code/", views.check_item_code, name="check_item_code"),

    # barcode page
    path('barcode/print/', views.print_barcode, name='print_barcode'),
    path("fetch-item-details/", views.fetch_item_details, name="fetch_item_details"),
    path('ajax/get-itemname1-info/', views.get_itemname1_info, name='get_itemname1_info'),
    path("label-sizes/", views.label_size_list, name="label_size_list"),
    path("label-sizes/add/", views.label_size_create, name="label_size_create"),
    path("label-sizes/<int:pk>/edit/", views.label_size_edit, name="label_size_edit"),
    path("label-sizes/<int:pk>/delete/", views.label_size_delete, name="label_size_delete"),

    # purchase page
    path('purchase/', views.purchase_view, name='purchase'),
    path('purchase_list/', views.purchase_list, name='purchase_list'),
    path('purchases/export/', views.export_purchases, name='export_purchases'),
    path('api/item/fetch/', views.fetch_item, name='fetch_item'),
    path('api/purchase/create/', views.create_purchase, name='create_purchase'),
    path('api/purchase/items/', views.fetch_purchase_items, name='fetch_purchase_items'),
    path('purchase/payment/', views.daily_purchase_payment_view, name='daily_purchase_payment'),
    path("get-invoice-details/", views.get_invoice_details, name="get_invoice_details"), 
    path('purchase/payments/', views.purchase_payment_list_view, name='purchase_payment_list'),  
    path('purchase/tracking/', views.purchase_tracking, name='purchase_update_tracking'),
    path("purchase/", views.purchase_page, name="purchase_page"),
    path('purchase_items/', views.purchase_items_view, name='purchase_items'),
    path('api/purchase-payments/<str:invoice_no>/', views.purchase_payments_api, name='purchase-payments-api'),

    # inventory page (first two not used)
    path('stock_adjustment/', views.stock_adjustment_view, name='stock_adjustment'),   
    path('stock_adjustments/', views.stock_adjustment_list, name='stock_adjustment_list'),
    path('split-stock/', views.split_stock_page, name='split_stock'),
    path('inventory/edit/<int:item_id>/', views.edit_bulk_item, name='edit_bulk_item'),
    path('ajax/fetch-item-info/', views.fetch_item_info, name='fetch_item_info'),
    path('inventory/', views.inventory_view, name='inventory'),

    path('product/<int:pk>/', views.product_detail, name='product_detail'),

    # supplier page 
    path('suppliers/', views.suppliers_view, name='suppliers'),
    path('suppliers/add/', views.add_supplier, name='add_supplier'),
    path('suppliers/edit/<int:supplier_id>/', views.edit_supplier, name='edit_supplier'),
    path('suppliers/delete/<int:supplier_id>/', views.delete_supplier, name='delete_supplier'),

    # customer page
    path('customers/', views.customers_view, name='customers'),
    path('add-customer/', views.add_customer, name='add_customer'),
    path('customers/edit/<int:id>/', views.edit_customer, name='edit_customer'),

    # # payments page (first two not used)
    path('payments/', views.payment_list_view, name='payment_list'),
    path('payments/<int:billing_id>/', views.get_payments, name='get_payments'),
    path('payments/', views.payment_list_view, name='payment-list'),
    path('billing/edit/<int:pk>/', views.billing_edit, name='billing_edit'),
    
    # expense page
    path('expense/',views.create_expense,name='expense'),
    path('expense/list/', views.expense_list, name='expense_list'),

    # company info page   
    path('company/', views.company_settings_view, name='company_details'),
    path('company-details/view/', views.view_company_details, name='view_company_details'),

    # logout page
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
]

handler403 = 'MahilMartPOS_App.views.custom_permission_denied_view'