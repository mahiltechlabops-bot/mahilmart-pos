from django.contrib import admin
from .models import Product, Category, Supplier
from django.contrib import admin
from .models import Customer
from .models import Billing


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'supplier', 'stock', 'reorder_level')
    list_filter = ('category', 'supplier')
    search_fields = ('name',)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_person', 'phone', 'email')
    search_fields = ('name', 'contact_person')

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'email', 'date_joined')
    search_fields = ('name', 'phone', 'email')


@admin.register(Billing)
class BillingAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'email', 'date_joined')
    search_fields = ('name', 'phone', 'email')