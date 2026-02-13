from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from django.conf.urls import handler403

urlpatterns = [
    # login page
    path('', views.login_view, name='home'),
    path("setup-admin/", views.initial_admin_setup, name="initial_admin_setup"),
    path("access-denied/", views.access_denied, name="access_denied"),

    path("settings/", views.settings_page, name="settings_page"),

    #create user
    path('users/create/', views.create_user, name='create_user'),
    path("settings/admin/", views.update_admin_settings, name="user"),
    path("settings/users/<int:user_id>/edit/", views.edit_user, name="edit_user"),
    path("settings/users/<int:user_id>/delete/", views.delete_user, name="delete_user"),
    path("ajax/search-users/", views.ajax_search_users, name="ajax_search_users"),

    # ---- AJAX GROUP MANAGEMENT (YOU MISSED THESE) ----
    path("ajax/get-groups/", views.ajax_get_groups, name="ajax_get_groups"),
    path("ajax/create-group/", views.ajax_create_group, name="ajax_create_group"),
    path("ajax/toggle-group/", views.ajax_toggle_group, name="ajax_toggle_group"),


    path("pos-theme/", views.pos_theme_view, name="pos_theme"),
    path("permission-settings/", views.permission_settings_view, name="permission_settings"),


    path("company/settings/", views.company_name_settings_view, name="company_name_settings"),
    path("company/activity/", views.company_activity_page, name="company_activity"),

    path("settings/email/", views.email_settings_view, name="email_settings"),
    path("settings/email/test/", views.email_test_view, name="email_test"),
    path("settings/email/view/", views.email_view_page, name="email_view"),
    path("settings/email/logs/", views.email_logs_view, name="email_logs"),
    path("settings/email/preview/", views.email_preview_view, name="email_preview"),


    # dashboard page
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('dashboard/transactions/', views.dashboard_transactions_api, name='dashboard_transactions_api'),
    path('computer-alias/', views.computer_alias_view, name='computer_alias'),

    #point config
    path("points-config/", views.points_config_view, name="points_config"),

    path('generate-report/', views.generate_report, name='generate_report'),
    path('reports/', views.reports_page, name='reports_page'),
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
    path('items/edit/<int:item_id>/', views.edit_item, name='edit_item'),
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
    path("api/purchase-products/", views.purchase_products_api, name="purchase_products_api"),
    path('api/purchase-payments/<str:invoice_no>/', views.purchase_payments_api, name='purchase-payments-api'),

    # B: safe path that accepts base64-encoded invoice (useful when invoices contain '/')
    path('api/purchase-payments/b64/<str:invoice_b64>/', views.purchase_payments_api_b64, name='purchase-payments-api-b64'),

    # (Optional) Query param endpoint (alternative)
    path('api/purchase-payments/', views.purchase_payments_api_query, name='purchase-payments-api-query'),

    # inventory page
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

    # payments page
    path('payments/', views.payment_list_view, name='payment_list'),
    path('payments/<int:billing_id>/', views.get_payments, name='get_payments'),
    path('payments/', views.payment_list_view, name='payment-list'),
    path('billing/edit/<int:pk>/', views.billing_edit, name='billing_edit'),

    # expense page
    path('expense/',views.create_expense,name='expense'),
    path('expense/list/', views.expense_list, name='expense_list'),
    path('expense/edit/<int:expense_id>/', views.edit_expense, name='expense_edit'),
    path('expense/delete/<int:expense_id>/', views.delete_expense, name='expense_delete'),

    # company info page
    path('company/', views.company_settings_view, name='company_details'),
    path('company-details/view/', views.view_company_details, name='view_company_details'),

    # logout page
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
    path('auto-logout/', views.auto_logout_on_close, name='auto_logout_on_close'),

    # migration
    path("db-migrate/", views.db_migration_tool, name="db_migration_tool"),
    path("db-migrate/ajax/load-mssql-tables/", views.ajax_load_mssql_tables, name="ajax_load_mssql_tables"),
    path("db-migrate/ajax/get-postgres-tables/", views.ajax_get_postgres_tables, name="ajax_get_postgres_tables"),
    path("db-migrate/ajax/get-columns/<str:table_name>/", views.ajax_get_columns, name="ajax_get_columns"),
    path("db-migrate/run/", views.migrate_single_table, name="migrate_single_table"),
    path("db-migrate/ajax/start-job/", views.start_migration_job, name="start_migration_job"),
    path("db-migrate/ajax/status/<uuid:job_id>/", views.migration_job_status, name="migration_job_status"),
    path("db-migrate/ajax/save-mapping/", views.ajax_save_mapping, name="ajax_save_mapping"),

    # activity log
    path("activity-log/", views.activity_log_view, name="activity_log"),
]

handler403 = 'MahilMartPOS_App.views.custom_permission_denied_view'
