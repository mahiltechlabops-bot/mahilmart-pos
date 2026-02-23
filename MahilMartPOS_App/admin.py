from django.contrib import admin
from .models import Category, Supplier
from django.contrib import admin
from .models import Customer,ComputerAlias
from .models import Billing
from django.contrib import admin
from .models import Company, CompanyActivity

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)

from django.contrib import admin
from .models import Supplier


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    # Columns shown in admin list
    list_display = (
        "supplier_id",
        "name",
        "contact_person",
        "phone",
        "email",
        "status",
    )

    # Search box fields
    search_fields = (
        "supplier_id",
        "name",
        "contact_person",
        "phone",
        "email",
    )

    # Filters on right sidebar
    list_filter = (
        "status",
    )

    # Default ordering
    ordering = (
        "supplier_id",
    )

    # Read-only fields (IMPORTANT)
    readonly_fields = (
        "supplier_id",
    )

    # Pagination
    list_per_page = 25

    # Field layout inside edit page
    fieldsets = (
        ("Supplier Info", {
            "fields": (
                "supplier_id",
                "name",
                "status",
            )
        }),
        ("Contact Details", {
            "fields": (
                "contact_person",
                "phone",
                "email",
                "address",
            )
        }),
        ("Business Details", {
            "fields": (
                "gst_number",
                "fssai_number",
                "pan_number",
                "credit_terms",
                "opening_balance",
            )
        }),
        ("Bank Details", {
            "fields": (
                "bank_name",
                "account_number",
                "ifsc_code",
            )
        }),
        ("Notes", {
            "fields": (
                "notes",
            )
        }),
    )


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'cell', 'email', 'date_joined')
    search_fields = ('name', 'cell', 'email')

admin.site.register(ComputerAlias)




@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'short_name', 'created_at')


@admin.register(CompanyActivity)
class CompanyActivityAdmin(admin.ModelAdmin):
    list_display = ('company', 'action', 'user', 'created_at')
    list_filter = ('company', 'created_at')
    search_fields = ('action', 'user__username')
