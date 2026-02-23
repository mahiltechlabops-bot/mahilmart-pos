from .models import (
    AdminSettings,
    CashierPermission,
    SupervisorPermission,
    CompanyDetails,
)


# =====================================================
# USER PERMISSIONS (optional standalone)
# =====================================================
def user_permissions(request):
    if not request.user.is_authenticated:
        return {"perm": None}

    user = request.user

    if user.is_superuser:
        return {"perm": None}

    if user.is_staff:
        perm = SupervisorPermission.objects.filter(user=user).first()
    else:
        perm = CashierPermission.objects.filter(user=user).first()

    return {"perm": perm}


# =====================================================
# BASE CONTEXT (theme + permissions)
# =====================================================
def base_context(request):
    theme = AdminSettings.objects.first()
    user = request.user
    perm = None

    if user.is_authenticated:

        if user.is_superuser:
            class FullPerm:
                allow_dashboard = True
                allow_billing = True
                allow_sales_return = True
                allow_products = True
                allow_items = True
                allow_purchase = True
                allow_inventory = True
                allow_suppliers = True
                allow_config_view = True
                allow_barcodes = True
                allow_reports = True
                allow_logs = True
                allow_company = True
                allow_customers = True
                allow_payments = True
                allow_expenses = True
                allow_settings = True
                allow_license_manager = True
            perm = FullPerm()

        elif user.is_staff:
            perm = SupervisorPermission.objects.filter(user=user).first()

        else:
            perm = CashierPermission.objects.filter(user=user).first()

    if perm is None:
        class DummyPerm:
            allow_dashboard = False
            allow_billing = False
            allow_sales_return = False
            allow_products = False
            allow_items = False
            allow_purchase = False
            allow_inventory = False
            allow_suppliers = False
            allow_config_view = False
            allow_barcodes = False
            allow_reports = False
            allow_logs = False
            allow_company = False
            allow_customers = False
            allow_payments = False
            allow_expenses = False
            allow_settings = False
            allow_license_manager = False
        perm = DummyPerm()

    return {
        "theme": theme,
        "perm": perm,
    }


# =====================================================
# COMPANY CONTEXT (GLOBAL STORE NAME)
# =====================================================
def company_context(request):
    company = CompanyDetails.objects.first()

    return {
        "company_name": (
            company.print_name
            if company and company.print_name
            else company.company_name
            if company else "MY STORE"
        ),
        "company_short_name": (
            company.short_name
            if company and company.short_name
            else "MM"
        ),
    }
