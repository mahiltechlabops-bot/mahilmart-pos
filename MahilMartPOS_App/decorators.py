# MahilMartPOS_App/decorators.py
from functools import wraps
from django.shortcuts import render

def access_required(allowed_roles=None):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return render(request, "base.html", {"access_denied": True})

            if allowed_roles:
                user_role = None
                if request.user.is_superuser:
                    user_role = 'superuser'
                elif request.user.is_staff:
                    user_role = 'staff'
                else:
                    user_role = 'user'

                if user_role not in allowed_roles:
                    return render(request, "base.html", {"access_denied": True})

            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

from functools import wraps
from django.shortcuts import redirect
from .models import CashierPermission, SupervisorPermission


# -------------------------
# Unified Permission Checker
# -------------------------
def _check_permission(user, perm_field):
    if not getattr(user, "is_authenticated", False):
        return False

    if user.is_superuser:
        return True

    # Load or create permission row for this user
    if user.is_staff:
        perm, _ = SupervisorPermission.objects.get_or_create(user=user)
    else:
        perm, _ = CashierPermission.objects.get_or_create(user=user)

    # Return True/False based on field
    return getattr(perm, perm_field, False)


# -------------------------
# Decorator Builder
# -------------------------
def build_permission_decorator(permission_name):
    perm_field = f"allow_{permission_name}"

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect("home")
            if _check_permission(request.user, perm_field):
                return view_func(request, *args, **kwargs)
            return redirect("access_denied")
        return wrapper

    return decorator


# -------------------------
# AUTO-CREATED DECORATORS
# -------------------------
allow_dashboard     = build_permission_decorator("dashboard")
allow_billing       = build_permission_decorator("billing")
allow_sales_return  = build_permission_decorator("sales_return")
allow_products      = build_permission_decorator("products")
allow_items         = build_permission_decorator("items")
allow_purchase      = build_permission_decorator("purchase")
allow_inventory     = build_permission_decorator("inventory")
allow_suppliers     = build_permission_decorator("suppliers")
allow_config_view   = build_permission_decorator("config_view")
allow_barcodes      = build_permission_decorator("barcodes")
allow_customers     = build_permission_decorator("customers")
allow_payments      = build_permission_decorator("payments")
allow_expenses      = build_permission_decorator("expenses")
allow_reports       = build_permission_decorator("reports")
allow_logs          = build_permission_decorator("logs")
allow_company       = build_permission_decorator("company")
allow_settings      = build_permission_decorator("settings")
allow_license_manager = build_permission_decorator("license_manager")
