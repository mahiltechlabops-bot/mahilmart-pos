import json
import os,datetime
import re
from django.db import models
from decimal import Decimal
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.db.models import Min, Q, Sum, FloatField
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.csrf import csrf_exempt
from .forms import SupplierForm, CompanySettingsForm
from django.db.models.functions import Trim
from datetime import datetime
from django.core.serializers import serialize
from django.contrib.auth.hashers import make_password, check_password
from django.core.paginator import Paginator
from .forms import OrderForm,OrderItem,ExpenseForm,PaymentForm,BillingForm,BillTypeForm,PaymentModeForm,CounterForm,PointsConfigForm,BillingConfigForm
from django.db import IntegrityError
from collections import defaultdict
from django.utils.timezone import localtime
from django.http import HttpResponse
from decimal import Decimal, ROUND_HALF_UP
from datetime import date        
from django.shortcuts import render, redirect
from django.shortcuts import redirect, HttpResponse
from .models import Quotation, Order, OrderItem
from django.utils import timezone
from django.db.models import F
from django.db.models import Q
from decimal import Decimal
from django.utils.timezone import now
from django.db.models import Max
from django.db.models import Sum, F
from django.db.models.functions import Abs, Coalesce, Cast
from django.utils.timezone import now, timedelta
from .models import Billing
from django.db.models import Sum, F, Case, When
from django.db.models import DecimalField, F, Sum, FloatField
from django.db.models import F, ExpressionWrapper, DecimalField, CharField, Value, Case, When
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.shortcuts import render, redirect
from .models import ComputerAlias, AdminSettings, CashierRestriction
from .models import LoginLog
from django.contrib.auth.models import User
import json
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.shortcuts import render
from .models import CashierPermission, SupervisorPermission
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from datetime import datetime, time
from django.utils.dateparse import parse_date
from django.contrib.auth.decorators import user_passes_test
from .decorators import access_required
from django.urls import reverse
from django.db import transaction
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Group
from django.contrib.sessions.models import Session
from django.http import HttpResponse
import io
from functools import wraps
from django.shortcuts import redirect
from .models import CashierPermission, SupervisorPermission
from django.shortcuts import render
from django.utils import timezone
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from types import SimpleNamespace
from django.http import JsonResponse
from django.template.loader import render_to_string
from barcode import Code128
from barcode.writer import ImageWriter

LOW_STOCK_THRESHOLD = float(getattr(settings, "LOW_STOCK_THRESHOLD", 10.0))


def _stock_qty_expr():
    return Case(
        When(
            Q(inventory__unit__icontains='bulk')
            | Q(unit__icontains='bulk')
            | Q(inventory__split_unit__gt=0, inventory__quantity__lte=0),
            then=Coalesce(F('inventory__split_unit'), Value(0.0)),
        ),
        default=Coalesce(F('inventory__quantity'), Value(0.0)),
        output_field=FloatField(),
    )


def _annotate_min_stock(qs):
    return (
        qs.annotate(
            min_stock_num=Case(
                When(
                    min_stock__regex=r'^\d+(\.\d+)?$',
                    then=Cast('min_stock', FloatField())
                ),
                default=Value(0.0),
                output_field=FloatField(),
            )
        )
        .annotate(
            min_stock_val=Case(
                When(min_stock_num__gt=0, then=F('min_stock_num')),
                default=Value(LOW_STOCK_THRESHOLD),
                output_field=FloatField(),
            )
        )
    )
from .models import (
    Supplier,
    Customer,
    Billing,
    BillingPayment,
    BillingItem,
    BillType,
    PaymentMode,
    Counter,
    BillingConfig,
    Item,  
    Unit,
    Group,
    Brand,
    Purchase,
    PurchaseItem,
    Tax,
    CompanyDetails,  
    StockAdjustment,
    PurchaseItem,
    Inventory,
    Order,
    Billing,
    Expense,
    Quotation,
    SaleReturn,
    SaleReturnItem,
    PurchasePayment,
    PurchaseTracking,
    DailyPurchasePayment,
    PointsConfig,
    LoginLog,
    ComputerAlias,
    BarcodeLabelSize,
)


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


from django.conf import settings
from django.shortcuts import render
from django.utils import timezone
from django.core.mail import EmailMultiAlternatives

from .utils.email_config import apply_email_settings  # ✅ NEW IMPORT


def access_denied(request):
    user = request.user if request.user.is_authenticated else None

    username = user.username if user else "Anonymous"
    full_name = user.get_full_name() if user else ""
    path = request.path
    method = request.method
    ip = request.META.get("REMOTE_ADDR", "Unknown IP")
    now = timezone.now().strftime("%Y-%m-%d %H:%M:%S")

    subject = "Access Denied Alert - MahilMart POS"

    # --------- PREMIUM HTML EMAIL TEMPLATE ----------
    html_message = f"""
    <div style="font-family: Arial, sans-serif; background:#f5f7fb; padding:20px;">
        <div style="max-width:600px; margin:auto; background:white; border-radius:12px;
                    box-shadow:0 4px 20px rgba(0,0,0,0.1); padding:25px;">

            <h2 style="color:#d9534f; text-align:center;">Access Denied Alert</h2>
            <p style="text-align:center; font-size:15px; color:#666;">
                A restricted page was accessed in <strong>MahilMart POS</strong>
            </p>

            <hr style="margin:20px 0;">

            <table style="width:100%; font-size:14px; color:#333;">
                <tr>
                    <td><strong>User:</strong></td>
                    <td>{username} {f'({full_name})' if full_name else ''}</td>
                </tr>
                <tr>
                    <td><strong>Authenticated:</strong></td>
                    <td>{request.user.is_authenticated}</td>
                </tr>
                <tr>
                    <td><strong>IP Address:</strong></td>
                    <td>{ip}</td>
                </tr>
                <tr>
                    <td><strong>Attempted Page:</strong></td>
                    <td>{path}</td>
                </tr>
                <tr>
                    <td><strong>Request Method:</strong></td>
                    <td>{method}</td>
                </tr>
                <tr>
                    <td><strong>Date & Time:</strong></td>
                    <td>{now}</td>
                </tr>
            </table>

            <hr style="margin:20px 0;">

            <div style="padding:10px; background:#f0f4ff; border-radius:8px;">
                <strong>GET Data:</strong>
                <pre style="font-size:13px; color:#555;">{dict(request.GET)}</pre>
            </div>

            <br>

            <div style="padding:10px; background:#f9f1f0; border-radius:8px;">
                <strong>POST Data:</strong>
                <pre style="font-size:13px; color:#555;">{dict(request.POST)}</pre>
            </div>

            <br>

            <p style="font-size:13px; text-align:center; color:#777;">
                This alert is generated automatically by <strong>MahilMart POS</strong>.
            </p>
        </div>
    </div>
    """

    # --------- SEND HTML EMAIL TO ADMINS ----------
    email_sent = False
    email_error = None
    support_email = None
    email_disabled = False

    try:
        # Apply database email settings (if configured)
        apply_email_settings()

        config = EmailConfig.objects.filter(is_active=True).first()
        recipients = []

        if config and not config.access_denied_alert_enabled:
            if config.alert_recipients:
                recipients = [e.strip() for e in config.alert_recipients.split(",") if e.strip()]
            if not recipients and config:
                fallback = config.default_from_email or config.email_host_user
                if fallback:
                    recipients = [fallback]
            if not recipients:
                recipients = [email for _, email in settings.ADMINS] if getattr(settings, "ADMINS", None) else []
            support_email = recipients[0] if recipients else None
            email_disabled = True
            return render(request, "access_denied.html", {
                "now": now,
                "support_email": support_email,
                "email_sent": False,
                "email_error": None,
                "email_disabled": True,
            }, status=403)

        if config and config.alert_recipients:
            recipients = [e.strip() for e in config.alert_recipients.split(",") if e.strip()]

        if not recipients and config:
            fallback = config.default_from_email or config.email_host_user
            if fallback:
                recipients = [fallback]

        if not recipients:
            recipients = [email for _, email in settings.ADMINS] if getattr(settings, "ADMINS", None) else []

        support_email = recipients[0] if recipients else None

        from_email = None
        if config:
            from_email = config.default_from_email or config.email_host_user
        if not from_email:
            from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or getattr(settings, "EMAIL_HOST_USER", None)

        if recipients and from_email:
            email = EmailMultiAlternatives(
                subject=subject,
                body="",  # plain text fallback
                from_email=from_email,
                to=recipients,
            )
            email.attach_alternative(html_message, "text/html")
            email.send(fail_silently=False)
            email_sent = True
            _safe_log_email(
                event_type="access_denied",
                subject=subject,
                recipients=", ".join(recipients),
                status="sent",
                triggered_by=user,
                request_path=path,
                ip_address=ip,
            )
        else:
            email_error = "Email settings or recipients are not configured."
            _safe_log_email(
                event_type="access_denied",
                subject=subject,
                recipients=", ".join(recipients),
                status="failed",
                error_message=email_error,
                triggered_by=user,
                request_path=path,
                ip_address=ip,
            )

    except Exception as e:
        email_error = f"Email could not be sent. {e}"
        print("Access denied email failed:", e)
        _safe_log_email(
            event_type="access_denied",
            subject=subject,
            recipients=", ".join(recipients) if "recipients" in locals() else "",
            status="failed",
            error_message=str(e),
            triggered_by=user,
            request_path=path,
            ip_address=ip,
        )

    return render(request, "access_denied.html", {
        "now": now,
        "support_email": support_email,
        "email_sent": email_sent,
        "email_error": email_error,
        "email_disabled": email_disabled,
    }, status=403)






def home(request):
    return render(request, 'home.html')

# # utils.py

# def get_client_ip(request):
#     x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
#     if x_forwarded_for:
#         return x_forwarded_for.split(",")[0]
#     return request.META.get("REMOTE_ADDR", "")
    

# def get_machine_id(request):
#     """Reads machine-id sent from browser (UUID saved in localStorage)"""
#     return request.POST.get("machine_id") or "Unknown-Device"

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.sessions.models import Session
from MahilMartPOS_App.models import LoginLog, ComputerAlias
from .utils.ip_utils import get_client_ip, get_machine_name_from_ip



def logout_previous_sessions(user):
    from django.contrib.sessions.models import Session

    for session in Session.objects.all():
        data = session.get_decoded()

        if data.get('_auth_user_id') == str(user.id):

            # Mark the session for forced logout
            data['force_logout'] = True
            session.delete()

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.sessions.models import Session
from django.utils import timezone

from MahilMartPOS_App.models import LoginLog, ComputerAlias

from .utils.ip_utils import get_client_ip, get_machine_name_from_ip



def login_view(request):
    from .models import CompanyDetails

    if not User.objects.filter(is_superuser=True).exists():
        return redirect("initial_admin_setup")

    def _get_branding_context():
        company = CompanyDetails.objects.first()
        app_name = "MY APP"
        app_short = "MM"
        if company:
            app_name = company.print_name or company.company_name or app_name
            app_short = company.short_name or app_short
        return {
            "app_name": app_name,
            "app_short": app_short,
            "app_tagline": "Enterprise Retail System",
            "app_version": "v1.0.0",
        }

    # ------------------------------------------
    # SHOW LOGIN PAGE (GET)
    # ------------------------------------------
    if request.method == 'GET':
        return render(request, "home.html", _get_branding_context())

    # ------------------------------------------
    # HANDLE FORM SUBMISSION (POST)
    # ------------------------------------------
    username = request.POST.get("username")
    password = request.POST.get("password")

    user = authenticate(request, username=username, password=password)

    if not user:
        context = _get_branding_context()
        context.update({
            "error": "Invalid credentials",
            "username": username
        })
        return render(request, "home.html", context)

    # ------------------------------------------
    # SUCCESS: LOGIN USER
    # ------------------------------------------
    login(request, user)

    # Ensure session key exists
    if not request.session.session_key:
        request.session.save()

    current_session_key = request.session.session_key

    # ------------------------------------------
    # DEVICE IDENTIFICATION
    # ------------------------------------------
    user_ip = get_client_ip(request)
    hostname = get_machine_name_from_ip(user_ip)
    fallback_id = request.POST.get("browser_machine_id")

    # Use real hostname if found; else browser ID
    machine_id = hostname if hostname != "Unknown-PC" else (fallback_id or "Unknown-Device")

    ComputerAlias.objects.get_or_create(
        computer_name=machine_id,
        defaults={"alias_name": machine_id}
    )

    # Save login history
    LoginLog.objects.create(
        user=user,
        ip_address=user_ip,
        computer_name=machine_id
    )

    # ------------------------------------------
    # SINGLE LOGIN ENFORCEMENT
    # Delete all old sessions except current
    # ------------------------------------------
    sessions = Session.objects.filter(expire_date__gte=timezone.now())
    for s in sessions:
        data = s.get_decoded()
        if str(data.get("_auth_user_id")) == str(user.id) and s.session_key != current_session_key:
            s.delete()

    # ------------------------------------------
    # REDIRECT TO DASHBOARD
    # ------------------------------------------
    return redirect("dashboard")


@csrf_exempt
def auto_logout_on_close(request):
    if request.method != "POST":
        return JsonResponse({"status": "method_not_allowed"}, status=405)

    if not request.user.is_authenticated:
        return JsonResponse({"status": "already_logged_out"})

    logout(request)
    return JsonResponse({"status": "ok"})


def initial_admin_setup(request):
    from .models import CompanyDetails

    if User.objects.filter(is_superuser=True).exists():
        return redirect("home")

    def _get_branding_context():
        company = CompanyDetails.objects.first()
        app_name = "MY APP"
        app_short = "MM"
        if company:
            app_name = company.print_name or company.company_name or app_name
            app_short = company.short_name or app_short
        return {
            "app_name": app_name,
            "app_short": app_short,
            "app_tagline": "Enterprise Retail System",
            "app_version": "v1.0.0",
        }

    context = _get_branding_context()
    context.update({
        "errors": [],
        "success": False,
        "form": {
            "username": "",
            "email": "",
        }
    })

    if request.method == "POST":
        username = (request.POST.get("username") or "").strip()
        email = (request.POST.get("email") or "").strip()
        password = request.POST.get("password") or ""
        confirm = request.POST.get("confirm_password") or ""

        context["form"]["username"] = username
        context["form"]["email"] = email

        if not username:
            context["errors"].append("Username is required.")
        if not password:
            context["errors"].append("Password is required.")
        if password and len(password) < 6:
            context["errors"].append("Password must be at least 6 characters.")
        if password != confirm:
            context["errors"].append("Passwords do not match.")
        if username and User.objects.filter(username=username).exists():
            context["errors"].append("Username already exists.")

        if not context["errors"]:
            User.objects.create_superuser(username=username, email=email, password=password)
            context["success"] = True

    return render(request, "admin_setup.html", context)










@allow_settings
@login_required
def create_user(request):
    from django.contrib.auth.models import Group

    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST.get('email')
        password = request.POST['password']
        role = request.POST.get('role')
        group_id = request.POST.get('group')     # <-- NEW

        # -------- VALIDATIONS ----------
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
            return redirect('create_user')

        if not group_id:
            messages.error(request, "Please select a group.")
            return redirect('create_user')

        # -------- CREATE USER ----------
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        # -------- ROLE ASSIGNMENT ----------
        if role == 'staff':
            user.is_staff = True

        elif role == 'admin':
            user.is_staff = True
            user.is_superuser = True

        user.save()

        # -------- GROUP ASSIGNMENT ----------
        try:
            group = Group.objects.get(id=group_id)
            user.groups.clear()            # remove old/default
            user.groups.add(group)         # assign new one
        except Group.DoesNotExist:
            messages.error(request, "Selected group does not exist.")
            return redirect('create_user')

        messages.success(request, "User created successfully.")
        return redirect('user')

    # ----- LOAD GROUPS FOR DROPDOWN -----
    groups = Group.objects.all()

    return render(request, 'create_user.html', {
        'groups': groups
    })




def ajax_get_groups(request):
    from django.contrib.auth.models import Group as AuthGroup
    groups = AuthGroup.objects.all().order_by("name")
    html = render_to_string("partials/group_list.html", {"groups": groups})
    return JsonResponse({"html": html})



def ajax_create_group(request):
    """Create a new group through modal."""
    try:
        from django.contrib.auth.models import Group as AuthGroup
        data = json.loads(request.body)

        group_name = data.get("group_name", "").strip()

        if not group_name:
            return JsonResponse({
                "success": False,
                "message": "Group name cannot be empty!"
            })

        if AuthGroup.objects.filter(name__iexact=group_name).exists():
            return JsonResponse({
                "success": False,
                "message": "Group already exists!"
            })

        group = AuthGroup.objects.create(name=group_name)

        return JsonResponse({
            "success": True,
            "id": group.id,
            "name": group.name
        })

    except Exception as e:
        return JsonResponse({
            "success": False,
            "message": str(e)
        })


from django.http import JsonResponse
from django.views.decorators.http import require_POST
from MahilMartPOS_App.models import Group
import json


@require_POST
def ajax_toggle_group(request):
    try:
        data = json.loads(request.body)
        group_id = data.get("id")

        group = Group.objects.get(id=group_id)
        group.is_active = not group.is_active
        group.save()

        return JsonResponse({
            "success": True,
            "is_active": group.is_active
        })

    except Group.DoesNotExist:
        return JsonResponse({
            "success": False,
            "message": "Group not found"
        })

    except Exception as e:
        return JsonResponse({
            "success": False,
            "message": str(e)
        })




@allow_settings
def settings_page(request):

    # Load admin settings (only 1 row)
    settings_obj, created = AdminSettings.objects.get_or_create(id=1)

    # ---------------------
    # SAVE ADMIN SETTINGS
    # ---------------------
    if request.method == "POST" and "save_admin" in request.POST:
        settings_obj.company_name = request.POST.get("company_name")
        settings_obj.phone = request.POST.get("phone")
        settings_obj.address = request.POST.get("address")
        settings_obj.invoice_footer = request.POST.get("invoice_footer")
        settings_obj.theme_color = request.POST.get("theme_color")
        settings_obj.save()
        return redirect("settings_page")

    # ---------------------
    # COMPUTER ALIAS SAVE
    # ---------------------
    if request.method == "POST" and "save_alias" in request.POST:
        comp_name = request.POST.get("computer_name")
        alias_name = request.POST.get("alias_name")
        ComputerAlias.objects.update_or_create(
            computer_name=comp_name,
            defaults={"alias_name": alias_name}
        )
        return redirect("settings_page")

    # ---------------------
    # CASHIER RESTRICTIONS SAVE
    # ---------------------
    if request.method == "POST" and "save_restriction" in request.POST:
        user_id = request.POST.get("user_id")
        user = User.objects.get(id=user_id)

        r, c = CashierRestriction.objects.get_or_create(user=user)
        r.allow_discount = "discount" in request.POST
        r.allow_price_edit = "price_edit" in request.POST
        r.allow_delete_bill = "delete_bill" in request.POST
        r.save()
        return redirect("settings_page")

    # List all computers seen in login logs
    all_computers = LoginLog.objects.values_list("computer_name", flat=True).distinct()
    pc_list = []
    for comp in all_computers:
        alias = ComputerAlias.objects.filter(computer_name=comp).first()
        pc_list.append({
            "computer_name": comp,
            "alias_name": alias.alias_name if alias else "",
        })

    # List all cashiers
    cashiers = User.objects.filter(groups__name="Cashier")

    restrictions = {r.user_id: r for r in CashierRestriction.objects.all()}
    default_license_tool_folder = os.path.join(
        os.path.expanduser("~"),
        "Documents",
        "MahilMartLicenseManager",
    )
    license_tool_folder_path = (
        os.environ.get("MAHILMARTPOS_LICENSE_TOOL_FOLDER")
        or default_license_tool_folder
    ).strip()
    license_tool_folder_uri = ""
    if license_tool_folder_path:
        try:
            from pathlib import Path

            license_tool_folder_uri = Path(license_tool_folder_path).resolve().as_uri()
        except Exception:
            license_tool_folder_uri = ""

    return render(request, "settings_page.html", {
        "settings_obj": settings_obj,
        "computers": pc_list,
        "cashiers": cashiers,
        "restrictions": restrictions,
        "license_tool_folder_path": license_tool_folder_path,
        "license_tool_folder_uri": license_tool_folder_uri,
    })

# ======================
# USER LIST (user_settings.html)
# ======================
from django.contrib.auth.models import Group

@allow_settings
def update_admin_settings(request):
    query = request.GET.get('q')
    sort_by = request.GET.get('sort', 'id')
    role = request.GET.get('role')  # this will be group name

    users = User.objects.all()

    # 🔍 Search
    if query:
        users = users.filter(Q(username__icontains=query) | Q(email__icontains=query))

    # 🔥 Filter By Group (role)
    if role:
        users = users.filter(groups__name=role)

    # 🔽 Sorting
    if sort_by in ['id', 'username', 'email']:
        users = users.order_by(sort_by)

    paginator = Paginator(users, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    # fetch group list for dropdown
    groups = Group.objects.all()

    return render(request, 'user_settings.html', {
        'page_obj': page_obj,
        'query': query,
        'sort_by': sort_by,
        'role': role,
        'groups': groups
    })


# ======================
# EDIT USER
# ======================
@allow_settings
def edit_user(request, user_id):
    from django.contrib.auth.models import Group

    user = get_object_or_404(User, id=user_id)

    if request.method == "POST":
        # Basic fields
        user.username = request.POST.get("username")
        user.email = request.POST.get("email")

        # Staff & Admin roles
        user.is_staff = True if request.POST.get("is_staff") == "on" else False
        user.is_superuser = True if request.POST.get("is_superuser") == "on" else False

        # Password update (optional)
        password = request.POST.get("password")
        if password:
            user.set_password(password)

        # -------------------------
        # SAVE GROUP SELECTION
        # -------------------------
        group_id = request.POST.get("group")
        if group_id:
            try:
                group = Group.objects.get(id=group_id)
                user.groups.clear()          # remove old groups
                user.groups.add(group)       # assign new group
            except Group.DoesNotExist:
                pass

        user.save()
        return redirect("user")

    # -------------------------
    # GET request data
    # -------------------------
    groups = Group.objects.all()
    current_group = user.groups.first()

    return render(request, "edit_user.html", {
        "user": user,
        "groups": groups,
        "current_group_id": current_group.id if current_group else None
    })


# ======================
# DELETE USER
# ======================
@allow_settings
def delete_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.delete()
    return redirect("user")

@user_passes_test(lambda u: u.is_superuser)
def ajax_search_users(request):
    query = request.GET.get("q", "").strip()
    
    users = User.objects.all()

    if len(query) >= 3:
        users = users.filter(
            Q(username__icontains=query) |
            Q(email__icontains=query)
        )

    html = render_to_string(
        "partials/user_table_rows.html", 
        {"users": users}
    )

    return JsonResponse({"html": html})
@allow_settings
def pos_theme_view(request):
    # Ensure settings object always exists
    settings = AdminSettings.objects.first()
    if settings is None:
        settings = AdminSettings.objects.create(
            primary_color="#2e3b4e",
            sidebar_color="#1f2a38",
            accent_color="#4a6fa5",
            mode="light"
        )

    if request.method == "POST":
        if "save_theme" in request.POST:

            # Save theme colors
            settings.primary_color = request.POST.get("primary_color")
            settings.sidebar_color = request.POST.get("sidebar_color")
            settings.accent_color = request.POST.get("accent_color")

            # Save theme mode (light / dark)
            settings.mode = request.POST.get("theme_mode") or "light"

            # Save logo
            if "logo" in request.FILES:
                settings.logo = request.FILES["logo"]

            settings.save()

            messages.success(request, "Theme updated successfully!")
            return redirect("pos_theme")

    return render(request, "pos_theme.html", {"settings": settings})


@allow_settings
def permission_settings_view(request):
    if not request.user.is_superuser:
        if request.method == "POST" and request.headers.get("Content-Type") == "application/json":
            return JsonResponse(
                {"status": "forbidden", "message": "Only super admin can change permission settings."},
                status=403,
            )
        messages.error(request, "Only super admin can access Permission Settings.")
        return redirect("access_denied")

    # -----------------------
    # AJAX auto-save handler
    # -----------------------
    if request.method == "POST" and request.headers.get("Content-Type") == "application/json":
        data = json.loads(request.body.decode("utf-8"))

        user_id = data.get("user")
        field = data.get("field")
        value = data.get("value") == "on"

        user = User.objects.get(id=user_id)

        # determine correct permission model
        if user.is_staff:
            perm, _ = SupervisorPermission.objects.get_or_create(user=user)
        else:
            perm, _ = CashierPermission.objects.get_or_create(user=user)

        setattr(perm, field, value)
        perm.save()

        return JsonResponse({"status": "ok"})

    # -----------------------
    # Normal GET page render
    # -----------------------
    user_id = request.GET.get("user")
    selected_user = User.objects.filter(id=user_id).first() if user_id else User.objects.filter(is_superuser=False).first()

    if not selected_user:
        return render(request, "permission_settings.html", {"users": [], "selected_user": None})

    if selected_user.is_staff:
        perm, _ = SupervisorPermission.objects.get_or_create(user=selected_user)
    else:
        perm, _ = CashierPermission.objects.get_or_create(user=selected_user)

    items = {
        "Dashboard": "allow_dashboard",
        "Billing": "allow_billing",
        "Sales Return": "allow_sales_return",
        "Products": "allow_products",
        "Items": "allow_items",
        "Purchase": "allow_purchase",
        "Inventory": "allow_inventory",
        "Suppliers": "allow_suppliers",
        "Config View": "allow_config_view",
        "Barcode Print": "allow_barcodes",
        "Reports": "allow_reports",
        "Activity Logs": "allow_logs",
        "Company Info": "allow_company",
        "Customers": "allow_customers",
        "Payments": "allow_payments",
        "Expenses": "allow_expenses",
        "Settings": "allow_settings",
        
    }

    users = User.objects.filter(is_superuser=False)

    alias_map = {}
    for alias_obj in ComputerAlias.objects.all().order_by("computer_name"):
        machine_name = (alias_obj.computer_name or "").strip()
        if not machine_name:
            continue
        alias_map[machine_name] = (alias_obj.alias_name or "").strip()

    login_machines = {
        (machine_name or "").strip()
        for machine_name in LoginLog.objects.values_list("computer_name", flat=True).distinct()
        if (machine_name or "").strip()
    }

    machine_names = sorted(set(alias_map.keys()) | set(login_machines))
    registered_computers = []
    for machine_name in machine_names:
        alias_name = alias_map.get(machine_name, "")
        registered_computers.append(
            {
                "computer_name": machine_name,
                "alias_name": alias_name or machine_name,
                "is_seen_in_logs": machine_name in login_machines,
            }
        )

    return render(request, "permission_settings.html", {
        "users": users,
        "selected_user": selected_user,
        "items": items,
        "perm": perm,
        "registered_computers": registered_computers,
    })


    


def custom_permission_denied_view(request, exception=None):
    from django.contrib import messages
    from django.shortcuts import redirect

    messages.error(request, "🚫 You do not have permission to access this page.")
    return redirect('dashboard')  # make sure 'dashboard' exists in urls.py

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from .models import Company, CompanyActivity
from .forms import CompanySettingsForm



@allow_company
@login_required
def company_settings_view(request):
    """
    Company Settings (Singleton Company)
    """

    # ✅ Always ensure ONE company exists
    company, created = Company.objects.get_or_create(
        id=1,
        defaults={
            "company_name": "My Company",
            "short_name": "MC",
            "created_by": request.user,
            "updated_by": request.user,
        }
    )

    if request.method == 'POST':
        # ✅ Update existing company, not create new
        form = CompanySettingsForm(request.POST, instance=company)

        if form.is_valid():
            instance = form.save(commit=False)
            instance.updated_by = request.user
            instance.save()

            # ✅ Backup logic (cleaned – no duplicate condition)
            if instance.auto_backup and instance.daily_backup_path:
                backup_company_details(instance, instance.daily_backup_path)

                # 🔹 Log backup activity
                CompanyActivity.objects.create(
                    company=instance,
                    user=request.user,
                    action="Company backup created"
                )

            # 🔹 Log update activity
            CompanyActivity.objects.create(
                company=instance,
                user=request.user,
                action="Company profile updated"
            )

            messages.success(request, "Company details saved successfully.")
            return redirect('company_details')

        else:
            messages.error(request, "There was an error in the form. Please check the fields.")

    else:
        # GET request → load existing data
        form = CompanySettingsForm(instance=company)

    # ✅ Recent activity (last 5)
    activities = CompanyActivity.objects.filter(
        company=company
    ).order_by('-created_at')[:5]

    context = {
        'form': form,
        'company': company,
        'activities': activities,
    }

    return render(request, 'company_details.html', context)

@allow_company
def view_company_details(request):
    company = CompanyDetails.objects.last()
    return render(request, 'view_company_details.html', {'company': company})

from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages

def allow_dashboard(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):

        # If user logged out because of multi-device login
        if not request.user.is_authenticated:
            messages.error(request, "You were logged out because your account was used on another device.")
            return redirect("home")   # message will show

        return view_func(request, *args, **kwargs)

    return wrapper

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from .models import CompanyDetails, Company, CompanyActivity
from .forms import CompanyNameForm

@allow_settings

def company_name_settings_view(request):
    company = CompanyDetails.objects.first()

    # Base company record for activity log (kept separate from CompanyDetails)
    base_company, _ = Company.objects.get_or_create(
        id=1,
        defaults={
            "company_name": company.company_name if company else "My Company",
            "short_name": company.short_name if company else "MC",
            "created_by": request.user if request.user.is_authenticated else None,
            "updated_by": request.user if request.user.is_authenticated else None,
        }
    )

    if request.method == "POST":
        form = CompanyNameForm(request.POST, instance=company)
        if form.is_valid():
            company_obj = form.save(commit=False)

            # Ensure required fields have safe defaults if not set
            if not company_obj.opening_time:
                company_obj.opening_time = time(9, 0)
            if not company_obj.closing_time:
                company_obj.closing_time = time(21, 0)
            if not company_obj.is_sunday_open:
                company_obj.is_sunday_open = "Open"

            # Fill required text fields with empty strings if missing
            required_text_fields = [
                "pincode",
                "state",
                "country",
                "phone",
                "mobile",
                "email",
                "gstin",
                "gst_type",
                "pan_no",
                "fssai_no",
                "trade_license_no",
                "invoice_prefix",
                "bank_name",
                "account_no",
                "ifsc_code",
            ]
            for field in required_text_fields:
                if getattr(company_obj, field, None) is None:
                    setattr(company_obj, field, "")

            if not company_obj.email:
                company_obj.email = "unknown@example.com"

            company_obj.save()
            CompanyActivity.objects.create(
                company=base_company,
                user=request.user if request.user.is_authenticated else None,
                action="Company name settings updated"
            )
            messages.success(request, "✅ Company details saved successfully")
            return redirect("company_name_settings")
    else:
        form = CompanyNameForm(instance=company)

    activities = CompanyActivity.objects.filter(
        company=base_company
    ).order_by('-created_at')[:5]

    return render(request, "company_name_settings.html", {
        "form": form,
        "company": company,
        "activities": activities
    })


@allow_settings
def company_activity_page(request):
    base_company, _ = Company.objects.get_or_create(
        id=1,
        defaults={
            "company_name": "My Company",
            "short_name": "MC",
            "created_by": request.user if request.user.is_authenticated else None,
            "updated_by": request.user if request.user.is_authenticated else None,
        }
    )

    activities = CompanyActivity.objects.filter(
        company=base_company
    ).order_by('-created_at')

    return render(request, "company_activity.html", {
        "company": base_company,
        "activities": activities,
    })

    
@allow_dashboard
@login_required(login_url='home')
def dashboard_view(request):

    # ======================================================
    # 🔐 1. ABSOLUTE SAFETY CHECK (handles auto-logout)
    # ======================================================
    user = request.user  # forces evaluation of SimpleLazyObject

    # If logged-out by your single-login system → stop immediately
    if not user.is_authenticated or '_auth_user_id' not in request.session:
        messages.error(
            request,
            "Your session ended because you logged in from another device."
        )
        return redirect('home')

    # ======================================================
    # 🔐 2. LOAD SIDEBAR PERMISSIONS SAFELY
    # ======================================================
    from .models import SupervisorPermission, CashierPermission

    if user.is_superuser:
        perm = None
    elif user.is_staff:
        perm = SupervisorPermission.objects.filter(user_id=user.id).first()
    else:
        perm = CashierPermission.objects.filter(user_id=user.id).first()

    # ======================================================
    # DATE SETUP
    # ======================================================
    today = now().date()
    yesterday = today - timedelta(days=1)

    # Billing query based on user role
    bills_qs = Billing.objects.all() if user.is_superuser else Billing.objects.filter(created_by=user)

    # ======================================================
    # TRANSACTION COUNT
    # ======================================================
    transaction_count = bills_qs.filter(created_at__date=today).count()

    # ======================================================
    # TODAY / YESTERDAY SALES
    # ======================================================
    today_sales = bills_qs.filter(date__date=today).aggregate(
        sum_total=Sum('items__amount')
    )['sum_total'] or 0

    yesterday_sales = bills_qs.filter(date__date=yesterday).aggregate(
        sum_total=Sum('items__amount')
    )['sum_total'] or 0

    change_percentage = (
        (today_sales - yesterday_sales) / yesterday_sales * 100
        if yesterday_sales > 0 else 0
    )
    if change_percentage > 100:
        change_percentage = 100

    # ======================================================
    # STOCK CALCULATION
    # ======================================================
    stock_qty_expr = _stock_qty_expr()

    stock_aggregates = (
        Item.objects.values('code', 'item_name', 'unit', 'min_stock')
        .annotate(
            total_qty=Coalesce(
                Sum(stock_qty_expr),
                Value(0.0),
                output_field=FloatField()
            )
        )
    )
    stock_aggregates = _annotate_min_stock(stock_aggregates)

    no_stock_items = stock_aggregates.filter(total_qty__lte=0)
    no_stock_count = no_stock_items.count()

    low_stock_items = stock_aggregates.filter(
        total_qty__gt=0,
        total_qty__lt=F('min_stock_val')
    )
    low_stock_count = low_stock_items.count()

    # Stock alert email (once per day)
    _send_stock_alert(request, low_stock_items, no_stock_items, low_stock_count, no_stock_count)

    # ======================================================
    # DATE RANGE FILTER FOR BILLS
    # ======================================================
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    bills_filtered = bills_qs.select_related('customer')

    if start_date or end_date:
        start = parse_date(start_date) if start_date else None
        end = parse_date(end_date) if end_date else None

        if start and end and start == end:
            bills_filtered = bills_filtered.filter(created_at__date=start)
        else:
            if start:
                bills_filtered = bills_filtered.filter(created_at__date__gte=start)
            if end:
                bills_filtered = bills_filtered.filter(created_at__date__lte=end)

    # ======================================================
    # HELPER — TOTAL RECEIVED
    # ======================================================
    def calculate_total_received(bill):
        payments_total = BillingPayment.objects.filter(billing=bill).aggregate(
            total=Sum('new_payment')
        )['total'] or Decimal('0')

        discount_amount = bill.discount_amt or Decimal('0')
        return (bill.received or Decimal('0')) + payments_total + discount_amount

    # ======================================================
    # RECENT BILLS LIST
    # ======================================================
    recent_bills = []
    for bill in bills_filtered.select_related('customer').order_by('-created_at'):
        total_received = calculate_total_received(bill)
        pending = bill.total_amount - total_received

        recent_bills.append({
            'id': bill.id,
            'bill_no': bill.bill_no,
            'received_amount': total_received,
            'date': bill.date,
            'customer_name': bill.customer.name if bill.customer else 'Walk-in',
            'customer_phone': bill.customer.cell if bill.customer else 'N/A',
            'sale_amount': bill.total_amount,
            'pending_amount': pending,
            'created_by': bill.created_by,
            'status': 'Pending' if pending > 0 else 'Completed',
        })

    # ======================================================
    # SALES TREND (LAST 30 DAYS)
    # ======================================================
    last_30_days = datetime.now() - timedelta(days=30)

    sales_trend = list(
        BillingItem.objects.filter(created_at__gte=last_30_days)
        .extra({'date': 'date(created_at)'})
        .values('date')
        .annotate(total_sales=Sum('amount'))
        .order_by('date')
    )

    # ======================================================
    # TOP SELLING PRODUCTS (30 DAYS DEFAULT)
    # ======================================================
    start_date_str = request.GET.get('top_start_date')
    end_date_str = request.GET.get('top_end_date')

    if start_date_str and end_date_str:
        top_start_date = parse_date(start_date_str)
        top_end_date = parse_date(end_date_str)
    else:
        top_end_date = today
        top_start_date = today - timedelta(days=30)

    top_selling = list(
        BillingItem.objects.filter(
            created_at__date__gte=top_start_date,
            created_at__date__lte=top_end_date
        ).values('item_name')
        .annotate(total_quantity=Sum('qty'))
        .order_by('-total_quantity')[:25]
    )

    # ======================================================
    # SALES BY CATEGORY
    # ======================================================
    default_start = today - timedelta(days=30)
    default_end = today

    cat_start = request.GET.get('category_start_date')
    cat_end = request.GET.get('category_end_date')

    category_start_date = parse_date(cat_start) if cat_start else default_start
    category_end_date = parse_date(cat_end) if cat_end else default_end

    item_groups = dict(Item.objects.values_list('item_name', 'group'))

    category_sales_dict = {}
    for bi in BillingItem.objects.filter(
        created_at__date__gte=category_start_date,
        created_at__date__lte=category_end_date
    ):
        group_name = item_groups.get(bi.item_name, 'Uncategorized')
        category_sales_dict[group_name] = category_sales_dict.get(group_name, 0) + bi.amount

    category_sales = sorted(
        [{'group': k, 'total_sales': v} for k, v in category_sales_dict.items()],
        key=lambda x: x['total_sales'],
        reverse=True
    )

    # ======================================================
    # REVENUE TOP PRODUCTS
    # ======================================================
    rev_start = request.GET.get('revenue_start_date')
    rev_end = request.GET.get('revenue_end_date')

    revenue_start_date = parse_date(rev_start) if rev_start else default_start
    revenue_end_date = parse_date(rev_end) if rev_end else default_end

    top_products = list(
        BillingItem.objects.filter(
            created_at__date__gte=revenue_start_date,
            created_at__date__lte=revenue_end_date
        )
        .values('item_name')
        .annotate(total_revenue=Sum('amount'))
        .order_by('-total_revenue')[:25]
    )

    # ======================================================
    # USERS & LOGIN STATUS
    # ======================================================
    active_users = User.objects.filter(is_active=True)

    admins_count = User.objects.filter(groups__name='Admin', is_active=True).count()
    supervisors_count = User.objects.filter(groups__name='Supervisor', is_active=True).count()
    cashiers_count = User.objects.filter(groups__name='Cashier', is_active=True).count()

    sessions = Session.objects.filter(expire_date__gte=timezone.now())
    session_user_ids = [
        int(s.get_decoded().get('_auth_user_id'))
        for s in sessions
        if s.get_decoded().get('_auth_user_id')
    ]

    user_details = []
    for u in active_users:
        if u.is_superuser:
            role = 'Admin'
        elif u.groups.filter(name='Supervisor').exists():
            role = 'Supervisor'
        elif u.groups.filter(name='Cashier').exists():
            role = 'Cashier'
        else:
            role = 'Other'

        last_log = LoginLog.objects.filter(user=u).order_by('-login_time').first()
        raw_machine_id = last_log.computer_name if last_log else "Unknown-Device"

        alias_obj = ComputerAlias.objects.filter(computer_name=raw_machine_id).first()
        alias_name = alias_obj.alias_name if alias_obj else raw_machine_id

        user_details.append({
            'username': u.username,
            'full_name': f"{u.first_name} {u.last_name}".strip() or '-',
            'role': role,
            'date_joined': u.date_joined,
            'last_login': u.last_login,
            'currently_logged_in': u.id in session_user_ids,
            'computer_name': raw_machine_id,
            'computer_alias': alias_name,
        })

    # ======================================================
    # CASH SUMMARY / BILLING SUMMARY
    # ======================================================
    bills = Billing.objects.filter(created_at__date=today)

    # Opening amount: derived from previous day's closing (database-based)
    prev_day = today - timedelta(days=1)
    prev_cash_received = BillingPayment.objects.filter(
        payment_date__date=prev_day,
        payment_mode="Cash"
    ).aggregate(total=Sum("new_payment"))["total"] or Decimal("0")

    prev_card_received = BillingPayment.objects.filter(
        payment_date__date=prev_day,
        payment_mode="Card"
    ).aggregate(total=Sum("new_payment"))["total"] or Decimal("0")

    prev_cash_received1 = Billing.objects.filter(
        created_at__date=prev_day
    ).aggregate(total=Sum("cash_amount"))["total"] or Decimal("0")

    prev_card_received1 = Billing.objects.filter(
        created_at__date=prev_day
    ).aggregate(total=Sum("card_amount"))["total"] or Decimal("0")

    prev_sale_refund = SaleReturn.objects.filter(
        created_at__date=prev_day
    ).aggregate(total=Sum("total_refund_amount"))["total"] or Decimal("0")

    prev_received_amt = prev_cash_received1 + prev_card_received1
    opening_amt = (
        prev_received_amt +
        (prev_cash_received + prev_card_received) -
        prev_sale_refund
    )

    total_sales = sum((b.total_amount for b in bills), Decimal("0"))

    todays_credit = bills.filter(bill_type="Credit").aggregate(
        total=Sum("balance")
    )["total"] or 0

    sale_refund = SaleReturn.objects.filter(
        created_at__date=today
    ).aggregate(total=Sum("total_refund_amount"))["total"] or 0

    cash_received = BillingPayment.objects.filter(
        payment_date__date=today,
        payment_mode="Cash"
    ).aggregate(total=Sum("new_payment"))["total"] or 0

    card_received = BillingPayment.objects.filter(
        payment_date__date=today,
        payment_mode="Card"
    ).aggregate(total=Sum("new_payment"))["total"] or 0

    cash_received1 = Billing.objects.filter(
        created_at__date=today
    ).aggregate(total=Sum("cash_amount"))["total"] or 0

    card_received1 = Billing.objects.filter(
        created_at__date=today
    ).aggregate(total=Sum("card_amount"))["total"] or 0

    received_amt = cash_received1 + card_received1

    closing_amt = (
        opening_amt + received_amt +
        (cash_received + card_received) -
        sale_refund
    )

    # ======================================================
    # FISCAL YEAR LABEL (from database if available)
    # ======================================================
    company_obj = CompanyDetails.objects.first()
    if company_obj and company_obj.year_from and company_obj.year_to:
        fiscal_year_label = f"{company_obj.year_from} - {company_obj.year_to}"
    else:
        fiscal_year_label = "Not set"

    # ======================================================
    # FINAL RENDER
    # ======================================================
    return render(request, 'dashboard.html', {
        'perm': perm,
        'transaction_count': transaction_count,
        'today_sales': today_sales,
        'yesterday_sales': yesterday_sales,
        'change_percentage': change_percentage,

        'no_stock_count': no_stock_count,
        'no_stock_items': no_stock_items,
        'low_stock_count': low_stock_count,
        'low_stock_items': low_stock_items,

        'recent_bills': recent_bills,

        'start_date': start_date,
        'end_date': end_date,

        'top_start_date': top_start_date,
        'top_end_date': top_end_date,

        'category_start_date': category_start_date,
        'category_end_date': category_end_date,

        'revenue_start_date': revenue_start_date,
        'revenue_end_date': revenue_end_date,

        'sales_trend': sales_trend,
        'top_selling': top_selling,
        'category_sales': category_sales,
        'top_products': top_products,

        'admin_count': admins_count,
        'supervisor_count': supervisors_count,
        'cashier_count': cashiers_count,

        'user_details': user_details,

        'opening_amt': opening_amt,
        'total_sales': total_sales,
        'todays_credit': todays_credit,
        'sale_refund': sale_refund,
        'cash_received': cash_received,
        'card_received': card_received,
        'cash_received1': cash_received1,
        'card_received1': card_received1,
        'received_amt': received_amt,
        'closing_amt': closing_amt,
        'fiscal_year_label': fiscal_year_label,
    })


@allow_dashboard
@login_required(login_url='home')
def dashboard_transactions_api(request):
    user = request.user

    if not user.is_authenticated or '_auth_user_id' not in request.session:
        return JsonResponse({"error": "unauthorized"}, status=401)

    bills_qs = Billing.objects.all() if user.is_superuser else Billing.objects.filter(created_by=user)

    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    bills_filtered = bills_qs.select_related('customer')

    if start_date or end_date:
        start = parse_date(start_date) if start_date else None
        end = parse_date(end_date) if end_date else None

        if start and end and start == end:
            bills_filtered = bills_filtered.filter(created_at__date=start)
        else:
            if start:
                bills_filtered = bills_filtered.filter(created_at__date__gte=start)
            if end:
                bills_filtered = bills_filtered.filter(created_at__date__lte=end)

    def calculate_total_received(bill):
        payments_total = BillingPayment.objects.filter(billing=bill).aggregate(
            total=Sum('new_payment')
        )['total'] or Decimal('0')

        discount_amount = bill.discount_amt or Decimal('0')
        return (bill.received or Decimal('0')) + payments_total + discount_amount

    transactions = []
    for bill in bills_filtered.order_by('-created_at'):
        total_received = calculate_total_received(bill)
        pending = bill.total_amount - total_received
        bill_date = localtime(bill.date).strftime('%d %b %Y %H:%M') if bill.date else ''

        transactions.append({
            'id': bill.id,
            'bill_no': bill.bill_no,
            'received_amount': float(total_received or 0),
            'sale_amount': float(bill.total_amount or 0),
            'pending_amount': float(pending or 0),
            'date': bill_date,
            'customer_name': bill.customer.name if bill.customer else 'Walk-in',
            'customer_phone': bill.customer.cell if bill.customer else 'N/A',
            'created_by': bill.created_by.username if bill.created_by else '',
            'status': 'Pending' if pending > 0 else 'Completed',
        })

    return JsonResponse({"transactions": transactions})


@allow_settings
def computer_alias_view(request):

    edit_id = request.GET.get("edit")
    delete_id = request.GET.get("delete")
    create_name = request.GET.get("create")

    # DELETE alias
    if delete_id:
        ComputerAlias.objects.filter(id=delete_id).delete()
        return redirect("computer_alias")

    # Object for edit mode
    edit_obj = None

    # Editing existing record
    if edit_id:
        edit_obj = ComputerAlias.objects.filter(id=edit_id).first()

    # Creating new alias for a computer without alias
    elif create_name:
        edit_obj = type("obj", (), {
            "id": "",
            "computer_name": create_name,
            "alias_name": ""
        })()

    # SAVE (Add / Update)
    if request.method == "POST":
        comp_name = request.POST.get("computer_name")
        alias_name = request.POST.get("alias_name")
        current_edit_id = request.POST.get("edit_id")

        # UPDATE only if ID is numeric
        if current_edit_id and current_edit_id.isdigit():
            ComputerAlias.objects.filter(id=current_edit_id).update(
                computer_name=comp_name,
                alias_name=alias_name
            )

        else:  # CREATE new alias
            ComputerAlias.objects.update_or_create(
                computer_name=comp_name,
                defaults={"alias_name": alias_name}
            )

        return redirect("computer_alias")

    # List all computers that logged in
    all_computers = LoginLog.objects.values_list("computer_name", flat=True).distinct()

    combined_aliases = []
    for comp in all_computers:
        alias = ComputerAlias.objects.filter(computer_name=comp).first()
        combined_aliases.append({
            "id": alias.id if alias else None,
            "computer_name": comp,
            "alias_name": alias.alias_name if alias else comp,
        })

    combined_aliases = sorted(combined_aliases, key=lambda x: x["alias_name"])

    return render(request, "computer_alias.html", {
        "aliases": combined_aliases,
        "edit_obj": edit_obj,
    })

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import PointsConfig

@login_required
def points_config_view(request):
    config = PointsConfig.objects.first()

    if request.method == "POST":
        value = request.POST.get("amount_for_one_point")

        if not value:
            return render(request, "points_config.html", {
                "config": config,
                "error": "Value is required"
            })

        if config:
            config.amount_for_one_point = value
            config.save()
        else:
            PointsConfig.objects.create(amount_for_one_point=value)

        return redirect("points_config")

    return render(request, "points_config.html", {"config": config})



@allow_billing
def generate_report(request):
    report_type = request.GET.get("reportType")
    today = now().date()
    yesterday = today - timedelta(days=1)

    data = {}

    if report_type == "Sales Report":
        total_sales = Billing.objects.aggregate(
            total=Sum(F('received') + F('balance'))
        )['total'] or 0

        data = {
            "total_sales": total_sales,
        }

    elif report_type == "User-wise Transaction Report":
        data = list(
            Billing.objects.values("created_by__username")
            .annotate(total_sales=Sum(F("received") + F("balance")))
            .order_by("created_by__username")
        )

    elif report_type == "Customer Report (Purchases & Outstanding)":
        data = list(
            Billing.objects.values("customer__name", "customer__cell")
            .annotate(
                total_purchases=Sum(F("received") + F("balance")),
                outstanding=Sum(F("balance")),
            )
            .order_by("customer__name")
        )

    elif report_type == "Inventory Report (Low Stock / Out of Stock)":
        # Keep inventory report consistent with dashboard stock calculations
        stock_qty_expr = _stock_qty_expr()

        stock_aggregates = (
            Item.objects.values('code', 'item_name', 'unit', 'min_stock')
            .annotate(
                total_qty=Coalesce(
                    Sum(stock_qty_expr),
                    Value(0.0),
                    output_field=FloatField()
                )
            )
        )
        stock_aggregates = _annotate_min_stock(stock_aggregates)

        no_stock_qs = stock_aggregates.filter(total_qty__lte=0)
        low_stock_qs = stock_aggregates.filter(
            total_qty__gt=0,
            total_qty__lt=F('min_stock_val')
        )

        data = {
            "low_stock": list(
                low_stock_qs.values("code", "item_name", "unit", "total_qty", "min_stock_val")
            ),
            "out_of_stock": list(
                no_stock_qs.values("code", "item_name", "unit", "total_qty", "min_stock_val")
            ),
            "low_stock_count": low_stock_qs.count(),
            "out_of_stock_count": no_stock_qs.count(),
        }

    elif report_type == "Revenue Report (Sales, Discounts, Returns)":
        data = Billing.objects.aggregate(
            total_sales=Sum(F("received") + F("balance")),
            total_discounts=Sum("discount"),
        )        

    return JsonResponse({
        "report_type": report_type,
        "data": data
    })

@allow_reports
def reports_page(request):
    # Sales summary
    total_sales = Billing.objects.aggregate(
        total=Sum(F('received') + F('balance'))
    )['total'] or 0

    # User-wise transactions
    user_transactions = list(
        Billing.objects.values("created_by__username")
        .annotate(total_sales=Sum(F("received") + F("balance")))
        .order_by("created_by__username")
    )

    # Customer report
    customer_report = list(
        Billing.objects.values("customer__name", "customer__cell")
        .annotate(
            total_purchases=Sum(F("received") + F("balance")),
            outstanding=Sum(F("balance")),
        )
        .order_by("customer__name")
    )

    # Inventory report (aggregate by item, include items with no stock)
    inventory_summary = (
        Item.objects
        .annotate(
            total_qty=Coalesce(
                Sum(_stock_qty_expr()),
                Value(0.0),
                output_field=FloatField()
            )
        )
    )
    inventory_summary = _annotate_min_stock(inventory_summary)

    low_stock = list(
        inventory_summary
        .filter(total_qty__gt=0, total_qty__lt=F('min_stock_val'))
        .values("code", "item_name", "total_qty", "min_stock_val")
        .order_by("total_qty")
    )
    out_of_stock = list(
        inventory_summary
        .filter(total_qty__lte=0)
        .values("code", "item_name", "total_qty", "min_stock_val")
        .order_by("item_name")
    )

    # Revenue report
    revenue = Billing.objects.aggregate(
        total_sales=Sum(F("received") + F("balance")),
        total_discounts=Sum("discount"),
    )

    context = {
        "total_sales": total_sales,
        "user_transactions": user_transactions,
        "customer_report": customer_report,
        "low_stock": low_stock,
        "out_of_stock": out_of_stock,
        "revenue": revenue,
    }
    return render(request, "reports.html", context)
@allow_billing
def billing_detail_view(request, id):
    bill = get_object_or_404(Billing, id=id)
    return render(request, 'billing_detail.html', {'bill': bill})
@allow_billing
def billing_items_api(request, bill_id):
    bill = get_object_or_404(Billing, id=bill_id)
    items = bill.items.all()  # use the related_name 'items'

    items_data = []
    for item in items:
        items_data.append({
            "code": item.code,
            "item_name": item.item_name,
            "unit": item.unit,
            "qty": float(item.qty),
            "mrp": float(item.mrp),
            "selling_price": float(item.selling_price),
            "amount": float(item.amount),
        })
    return JsonResponse({"items": items_data})
    
@allow_billing
def sales_chart_data(request):
    today = timezone.localdate()
    week_start = today - timedelta(days=today.weekday())  # Monday
    month_start = today.replace(day=1)

    def get_sales(start_date, end_date):
        # Annotate amount = received + (-balance)
        raw_data = (
            Billing.objects
            .filter(created_at__date__gte=start_date, created_at__date__lte=end_date)
            .annotate(
                amount=ExpressionWrapper(
                    F('received') + (-F('balance')),
                    output_field=DecimalField()
                )
            )
            .values('created_at__date')
            .annotate(total=Sum('amount'))
            .order_by('created_at__date')
        )

        # Convert to dict {date: total}
        data_dict = {str(row['created_at__date']): float(row['total']) for row in raw_data}

        # Fill missing days with 0
        result = []
        current_date = start_date
        while current_date <= end_date:
            date_str = str(current_date)
            result.append({
                'date': date_str,
                'total': data_dict.get(date_str, 0.0)
            })
            current_date += timedelta(days=1)
        return result

    # Weekly & monthly ranges
    week_data = get_sales(week_start, today)
    month_data = get_sales(month_start, today)

    weekly_total = sum(d['total'] for d in week_data)
    monthly_total = sum(d['total'] for d in month_data)

    return JsonResponse({
        'week': week_data,
        'month': month_data,
        'weekly_total': weekly_total,
        'monthly_total': monthly_total
    })



from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from types import SimpleNamespace
import json
import traceback

from MahilMartPOS_App.models import (
    Customer, Billing, BillingItem, Inventory,
    BillType, PaymentMode, Counter,
    PointsConfig, BillingConfig,
    CompanyDetails, LoginLog, ComputerAlias
)

from .decorators import allow_billing


@allow_billing
@login_required
def create_invoice_view(request):

    # ==========================================================
    # COMPANY & BUSINESS TYPE (GLOBAL – FIXES ERROR)
    # ==========================================================
    company_obj = CompanyDetails.objects.first()
    business_type = (
        company_obj.business_type.name
        if company_obj and company_obj.business_type
        else "retail"
    )

    # ==========================================================
    # AJAX: Fetch customer by phone
    # ==========================================================
    if (
        request.method == "GET"
        and request.headers.get("x-requested-with") == "XMLHttpRequest"
        and request.GET.get("phone")
    ):
        phone = request.GET.get("phone").strip()
        customer = Customer.objects.filter(cell=phone).first()

        return JsonResponse({
            "exists": bool(customer),
            "name": customer.name if customer else None,
            "points": float(customer.total_points) if customer else 0.0,
            "email": customer.email if customer else "",
            "customer_address": customer.address if customer else "",
            "date_joined": (
                customer.date_joined.date().isoformat()
                if customer and customer.date_joined
                else ""
            ),
        })

    # ==========================================================
    # POST: Save invoice
    # ==========================================================
    if request.method == "POST":
        try:
            with transaction.atomic():

                # ------------------------------
                # CUSTOMER
                # ------------------------------
                cell = (request.POST.get("cell") or "").strip()
                name = (request.POST.get("name") or "").strip()
                email = (request.POST.get("email") or "").strip()
                address = (request.POST.get("address") or "").strip()

                if not cell or not name:
                    raise ValueError("Customer name and phone are required")

                customer, created = Customer.objects.get_or_create(
                    cell=cell,
                    defaults={
                        "name": name,
                        "email": email,
                        "address": address,
                        "total_points": 0,
                    },
                )

                if not created:
                    if name:
                        customer.name = name
                    if email:
                        customer.email = email
                    if address:
                        customer.address = address
                    customer.save()

                # ------------------------------
                # BILL NUMBER
                # ------------------------------
                latest = Billing.objects.order_by("-id").first()
                bill_no = (
                    str(int(latest.bill_no) + 1)
                    if latest and str(latest.bill_no).isdigit()
                    else "1"
                )

                # ------------------------------
                # POINTS
                # ------------------------------
                old_points = float(customer.total_points or 0)
                today_points = float(request.POST.get("total_earned") or 0)
                new_total_points = old_points + today_points

                # ------------------------------
                # ITEMS
                # ------------------------------
                raw_items = request.POST.get("item_data")
                if not raw_items:
                    raise ValueError("No items received")

                items = json.loads(raw_items)

                total_sale_amount = sum(
                    float(i.get("amount") or 0) for i in items
                )

                discount_percent = float(request.POST.get("discount") or 0)
                discount_amt = total_sale_amount * discount_percent / 100

                # ------------------------------
                # PAYMENTS
                # ------------------------------
                cash = float(request.POST.get("cash_amount") or 0)
                card = float(request.POST.get("card_amount") or 0)
                received = float(request.POST.get("received") or 0)
                balance = float(request.POST.get("balance") or 0)

                # ------------------------------
                # CREATE BILLING
                # ------------------------------
                billing = Billing.objects.create(
                    customer=customer,
                    bill_no=bill_no,
                    date=timezone.now(),
                    cash_amount=cash,
                    card_amount=card,
                    received=received,
                    balance=max(balance, 0),
                    bill_type=request.POST.get("bill_type"),
                    counter=request.POST.get("counter"),
                    order_no=request.POST.get("order_no"),
                    sale_type=request.POST.get("sale_type"),
                    discount=discount_percent,
                    discount_amt=discount_amt,
                    points=new_total_points,
                    points_earned=today_points,
                    remarks=request.POST.get("remarks", ""),
                    status_on="counter_bill",
                    created_by=request.user,
                )

                # ------------------------------
                # FIFO STOCK + BILL ITEMS
                # ------------------------------
                for row in items:
                    code = row.get("code")
                    item_name = row.get("item_name")
                    unit = row.get("unit")
                    qty = float(row.get("qty") or 0)
                    mrp = float(row.get("mrsp") or 0)
                    selling_price = float(row.get("sellingprice") or 0)
                    amount = qty * selling_price

                    remaining_qty = qty

                    inventory_qs = Inventory.objects.filter(
                        code=code,
                        status="in_stock",
                        quantity__gt=0,
                    )

                    if business_type == "medical":
                        inventory_qs = inventory_qs.exclude(
                            expiry_date__lt=timezone.now().date()
                        )

                    inventory_qs = inventory_qs.order_by("purchased_at", "id")

                    for inv in inventory_qs:
                        if remaining_qty <= 0:
                            break

                        is_bulk = "bulk" in (inv.unit or "").lower()

                        if is_bulk:
                            available = inv.split_unit or 0
                            deduct = min(available, remaining_qty)
                            inv.split_unit -= deduct
                            inv.quantity -= deduct / (inv.unit_qty or 1)
                        else:
                            available = inv.quantity or 0
                            deduct = min(available, remaining_qty)
                            inv.quantity -= deduct

                        if inv.quantity <= 0:
                            inv.status = "completed"

                        inv.save()
                        remaining_qty -= deduct

                    if remaining_qty > 0:
                        raise ValueError(f"Insufficient stock for {item_name}")

                    BillingItem.objects.create(
                        billing=billing,
                        customer=customer,
                        code=code,
                        item_name=item_name,
                        unit=unit,
                        qty=qty,
                        mrp=mrp,
                        selling_price=selling_price,
                        amount=amount,
                    )

                # ------------------------------
                # UPDATE CUSTOMER POINTS
                # ------------------------------
                customer.total_points = new_total_points
                customer.save(update_fields=["total_points"])

                messages.success(request, "✅ Billing submitted successfully")
                return redirect("billing")

        except Exception as e:
            traceback.print_exc()
            messages.error(request, f"Billing failed: {e}")

    # ==========================================================
    # GET: Render billing page
    # ==========================================================
    latest_bill = Billing.objects.order_by("-id").first()
    next_bill_no = (
        str(int(latest_bill.bill_no) + 1)
        if latest_bill and str(latest_bill.bill_no).isdigit()
        else "1"
    )

    today_date = timezone.now().strftime("%Y-%m-%d")

    company = SimpleNamespace(
        short_name=company_obj.short_name if company_obj else "MM",
        company_name=company_obj.company_name if company_obj else "MY STORE",
        print_name=company_obj.print_name if company_obj else None,
        address=company_obj.address if company_obj else "",
        gstin=company_obj.gstin if company_obj else "",
        mobile=company_obj.mobile if company_obj else "",
        phone=company_obj.phone if company_obj else "",
        website=company_obj.website if company_obj else "",
    )

    points_config = PointsConfig.objects.order_by("-updated_at").first()
    amount_for_one_point = points_config.amount_for_one_point if points_config else 200

    billing_config = BillingConfig.objects.order_by("-id").first()
    enable_gst = billing_config.enable_gst if billing_config else False

    last_log = LoginLog.objects.filter(user=request.user).order_by("-login_time").first()
    raw_computer_name = last_log.computer_name if last_log else ""
    alias_obj = ComputerAlias.objects.filter(computer_name=raw_computer_name).first()
    current_counter_name = alias_obj.alias_name if alias_obj else raw_computer_name

    return render(request, "billing.html", {
        "today_date": today_date,
        "bill_no": next_bill_no,
        "bill_types": BillType.objects.all().order_by("billtype_id"),
        "payment_modes": PaymentMode.objects.all(),
        "counter": Counter.objects.all().order_by("counter_id"),
        "company": company,
        "business_type": business_type,  # ✅ SAFE NOW
        "amount_for_one_point": amount_for_one_point,
        "enable_gst": enable_gst,
        "current_counter_name": current_counter_name,
    })





from decimal import Decimal
from django.http import JsonResponse
from django.utils import timezone

@allow_billing
def get_item_info(request):
    code = request.GET.get('code', '').strip()
    name = request.GET.get('name', '').strip()

    # --------------------------------------------------
    # STEP 1: FIND ITEM
    # --------------------------------------------------
    item = None

    if code:
        item = Item.objects.filter(code__iexact=code).first()
        if not item:
            item = Item.objects.filter(barcode__iexact=code).first()
    elif name:
        item = Item.objects.filter(item_name__icontains=name).first()

    if not item:
        return JsonResponse({'error': 'Item not found'}, status=404)

    unit_name = item.unit or ""
    is_bulk = "bulk" in unit_name.lower()

    # --------------------------------------------------
    # STEP 2: FIFO INVENTORY (NON-EXPIRED ONLY)
    # --------------------------------------------------
    inventory_qs = Inventory.objects.filter(
        code=item.code,
        status="in_stock",
        quantity__gt=0
    ).exclude(
        expiry_date__lt=timezone.now().date()
    ).order_by('purchased_at', 'batch_no', 'id')

    if not inventory_qs.exists():
        return JsonResponse({
            'item_name': item.item_name,
            'item_code': item.code,
            'unit': unit_name,
            'is_bulk': is_bulk,
            'current_mrp': 0,
            'tax': float(item.tax or 0),
            'total_available': 0,
            'low_stock_warning': True,
            'warning_message': "⚠️ No stock available",
            'batch_details': [],
            'all_batch_nos': []
        })

    # --------------------------------------------------
    # STEP 3: FIRST FIFO MRP
    # --------------------------------------------------
    current_mrp = round(float(inventory_qs.first().mrp_price or 0), 2)

    total_available = Decimal("0")
    low_stock_batches = []
    merged_batches = []
    all_batch_nos = []

    # --------------------------------------------------
    # STEP 4: PROCESS SAME-MRP BATCHES ONLY
    # --------------------------------------------------
    for inv in inventory_qs:
        batch_mrp = round(float(inv.mrp_price or 0), 2)
        if batch_mrp != current_mrp:
            break

        available = Decimal(inv.split_unit if is_bulk else inv.quantity or 0)

        total_available += available
        all_batch_nos.append(inv.batch_no)

        row = {
            "batch_no": inv.batch_no,
            "available_qty": float(available),
            "mrp": batch_mrp,
            "split_sale_price": round(float(inv.sale_price or 0), 2),
            "purchased_at": inv.purchased_at.strftime("%Y-%m-%d") if inv.purchased_at else "",
            "status": inv.status,
        }

        # Merge rows with same MRP
        if merged_batches and merged_batches[-1]["mrp"] == batch_mrp:
            merged_batches[-1]["available_qty"] += row["available_qty"]
            merged_batches[-1]["batch_no"] += f", {row['batch_no']}"
        else:
            merged_batches.append(row)

        if available < LOW_STOCK_THRESHOLD:
            low_stock_batches.append(f"{inv.batch_no} (qty: {available})")

    # --------------------------------------------------
    # STEP 5: ROUND
    # --------------------------------------------------
    for batch in merged_batches:
        batch["available_qty"] = round(batch["available_qty"], 2)

    # --------------------------------------------------
    # STEP 6: WARNINGS
    # --------------------------------------------------
    if total_available == 0:
        warning_message = "⚠️ No stock available"
    elif low_stock_batches:
        warning_message = f"⚠️ Low stock in batch(es): {', '.join(low_stock_batches)}"
    else:
        warning_message = ""

    return JsonResponse({
        "item_name": item.item_name,
        "item_code": item.code,
        "unit": unit_name,
        "is_bulk": is_bulk,
        "current_mrp": current_mrp,
        "tax": float(item.tax or 0),
        "total_available": round(float(total_available), 2),
        "low_stock_warning": bool(low_stock_batches),
        "warning_message": warning_message,
        "batch_details": merged_batches,
        "all_batch_nos": all_batch_nos,
    })


@allow_billing
def get_itemname_info(request):
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse({'suggestions': []})

    items = Item.objects.filter(
        item_name__icontains=query
    ).order_by("item_name")[:25]

    return JsonResponse({
        "suggestions": [
            {
                "item_code": i.code,
                "item_name": i.item_name,
                "unit": i.unit,
            }
            for i in items
        ]
    })


@allow_config_view
def add_billtype(request):

    # -----------------------------
    # AUTO ID HELPERS
    # -----------------------------
    def auto_id(qs):
        n = 1
        for i in qs:
            if i != n:
                break
            n += 1
        return n

    billtype_next_id = auto_id(
        BillType.objects.values_list("billtype_id", flat=True).order_by("billtype_id")
    )
    paymentmode_next_id = auto_id(
        PaymentMode.objects.values_list("mode_id", flat=True).order_by("mode_id")
    )
    counter_next_id = auto_id(
        Counter.objects.values_list("counter_id", flat=True).order_by("counter_id")
    )

    billtype_form = BillTypeForm(initial={"billtype_id": billtype_next_id})
    paymentmode_form = PaymentModeForm(initial={"mode_id": paymentmode_next_id})
    counter_form = CounterForm(initial={"counter_id": counter_next_id})

    points_config = PointsConfig.objects.first()
    points_form = PointsConfigForm(instance=points_config)

    billtype_form.fields["billtype_id"].initial = billtype_next_id
    paymentmode_form.fields["mode_id"].initial = paymentmode_next_id
    counter_form.fields["counter_id"].initial = counter_next_id

    # -----------------------------
    # POST HANDLING
    # -----------------------------
    if request.method == "POST":

        if "save_billtype" in request.POST:
            form = BillTypeForm(request.POST)
            if form.is_valid():
                form.save()
                return redirect("add")

        elif "save_paymentmode" in request.POST:
            form = PaymentModeForm(request.POST)
            if form.is_valid():
                form.save()
                return redirect("add")

        elif "save_counter" in request.POST:
            form = CounterForm(request.POST)
            if form.is_valid():
                form.save()
                return redirect("add")

        elif "save_points" in request.POST:
            form = PointsConfigForm(request.POST)
            if form.is_valid():
                form.save()
                return redirect("add")

        elif "save_billing_config" in request.POST:
            billing_config, _ = BillingConfig.objects.get_or_create(id=1)
            form = BillingConfigForm(request.POST, instance=billing_config)
            if form.is_valid():
                form.save()
                return redirect("add")

    billing_config, _ = BillingConfig.objects.get_or_create(id=1)

    return render(request, "add_billtype.html", {
        "billtype_form": billtype_form,
        "paymentmode_form": paymentmode_form,
        "counter_form": counter_form,
        "points_form": points_form,
        "config": billing_config,
    })


@allow_payments
def order_payments(request, order_id):
    payments = Order.objects.filter(order_id=order_id).values(
        'order_id', 'customer_name', 'total_amount', 
        'advance_paid', 'new_payment', 'due_balance', 
        'payment_mode', 'payment_date'
    )
    payments_list = list(payments)
    return JsonResponse({'payments': payments_list})

@allow_payments
def billing_edit(request, pk):
    bill = get_object_or_404(Billing, pk=pk)

    payments = BillingPayment.objects.filter(billing=bill).aggregate(
        total_paid=Sum('new_payment')
    )

    # Calculate total already paid from BillingPayment
    total_paid = bill.received or Decimal('0')

    # FIXED: Discount apply as percentage
    discounted_total = (bill.total_amount or Decimal('0')) - (   
        (bill.total_amount or Decimal('0')) * (bill.discount or Decimal('0')) / 100
    )

    balance_amount = discounted_total - total_paid

    if request.method == "POST":
        form = BillingForm(request.POST, instance=bill)
        new_payment = request.POST.get("new_payment")
        payment_mode = request.POST.get("payment_mode", "Cash")

        if form.is_valid():
            if new_payment and float(new_payment) > 0:
                new_payment_decimal = Decimal(new_payment)
                total_paid_before = total_paid

                # Create BillingPayment
                BillingPayment.objects.create(
                    billing=bill,
                    customer=bill.customer,
                    total_amount=bill.total_amount,
                    already_paid=total_paid_before,
                    new_payment=new_payment_decimal,
                    balance=discounted_total - (total_paid_before + new_payment_decimal),
                    payment_date=timezone.now(),
                    payment_mode=payment_mode
                )

                # Update Billing amounts based on payment mode
                if payment_mode == "Cash":
                    bill.cash_amount = (bill.cash_amount or Decimal('0')) + new_payment_decimal
                elif payment_mode == "Card":
                    bill.card_amount = (bill.card_amount or Decimal('0')) + new_payment_decimal
                elif payment_mode == "Online":
                    bill.online_amount = (bill.online_amount or Decimal('0')) + new_payment_decimal

                # Update total received
                bill.received = (bill.received or Decimal('0')) + new_payment_decimal
                if bill.received >= bill.total_amount:
                        cash_amt = bill.cash_amount or Decimal('0')
                        card_amt = bill.card_amount or Decimal('0')

                        if cash_amt > 0 and card_amt > 0:
                            bill.bill_type = "Both Cash & Card"
                        elif cash_amt > 0 and card_amt == 0:
                            bill.bill_type = "Cash"
                        elif card_amt > 0 and cash_amt == 0:
                            bill.bill_type = "Card"
                        else:
                            bill.bill_type = "Cash"  

                bill.save()

                try:
                    order = Order.objects.get(bill_no=bill.bill_no)
                    order.advance = bill.received
                    order.due_balance = bill.total_amount - bill.received
                    order.order_status = 'completed' if order.due_balance <= 0 else 'pending'
                    order.save()
                except Order.DoesNotExist:
                    pass
            else:
                form.save()

            return redirect("payment_list")
    else:
        form = BillingForm(instance=bill)

    return render(request, "billing_edit.html", {
        "form": form,
        "bill": bill,
        "total_paid": total_paid,
        "balance_amount": balance_amount,
        "discounted_total": discounted_total
    })

@allow_payments
def payment_list_view(request):
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    payment_mode = request.GET.get('payment_mode')

    billings = Billing.objects.select_related('customer').all().order_by('-id')

    if from_date and to_date:
        billings = billings.filter(date__date__gte=from_date, date__date__lte=to_date)
    elif from_date:
        billings = billings.filter(date__date__gte=from_date)
    elif to_date:
        billings = billings.filter(date__date__lte=to_date)

    # Payment mode filter
    if payment_mode and payment_mode != 'all':
        billings = billings.filter(bill_type__iexact=payment_mode)

    for bill in billings:
        # Aggregated payments
        payments = BillingPayment.objects.filter(billing=bill).aggregate(
            total_paid=Sum('new_payment')
        )

        # Normalize values to Decimal
        total_amount = bill.total_amount or Decimal("0")
        discount = bill.discount or Decimal("0")
        total_received = bill.received or Decimal("0")

        # Handle cash/card split safely
        cash_paid = Decimal("0")
        card_paid = Decimal("0")

        if bill.bill_type == "Cash":
            cash_paid = bill.cash_amount or total_received
        elif bill.bill_type == "Card":
            card_paid = bill.card_amount or total_received
        elif bill.bill_type == "Both Cash & Card":
            cash_paid = bill.cash_amount or Decimal("0")
            card_paid = bill.card_amount or Decimal("0")
        elif bill.bill_type == "Credit":
            cash_paid = bill.cash_amount or Decimal("0")
            card_paid = bill.card_amount or Decimal("0")

        # Apply discount correctly with Decimal
        discounted_total = total_amount - (total_amount * discount / Decimal("100"))
        balance_amount = discounted_total - total_received

        # Attach computed values to bill
        bill.total_received = total_received
        bill.balance_amount = balance_amount
        bill.cash_paid = cash_paid
        bill.card_paid = card_paid
        bill.display_total_amount = discounted_total

        # Determine payment status
        if bill.bill_type.lower() == 'credit':
            if total_received == 0:
                bill.payment_status = 'Unpaid'
                bill.status_class = 'status-unpaid'
            elif total_received < total_amount:
                bill.payment_status = 'Partially Paid'
                bill.status_class = 'status-partial'
            else:
                bill.payment_status = 'Paid'
                bill.status_class = 'status-paid'
        else:
            bill.payment_status = 'Paid'
            bill.status_class = 'status-paid'

    # Totals across all bills
    total_amount = sum((b.total_amount or Decimal("0")) for b in billings)
    total_paid = sum((b.total_received or Decimal("0")) for b in billings)
    total_balance = sum((b.balance_amount or Decimal("0")) for b in billings)
    total_cash = sum((b.cash_paid or Decimal("0")) for b in billings)
    total_card = sum((b.card_paid or Decimal("0")) for b in billings)

    return render(request, 'payments.html', {
        'billings': billings,
        'from_date': from_date,
        'to_date': to_date,
        'payment_mode': payment_mode,
        'total_paid': total_paid,
        'total_balance': total_balance,
        'total_cash': total_cash,
        'total_card': total_card,
        'total_amount': total_amount
    })

@allow_payments
def get_payments(request, billing_id):
    payments = BillingPayment.objects.filter(billing_id=billing_id).order_by('payment_date')
    data = []
    for i, p in enumerate(payments, start=1):
        data.append({
            'sno': i,
            'bill_no': p.bill_no,
            'customer': p.customer.name,
            'total_amount': float(p.total_amount),
            'already_paid': float(p.already_paid),
            'new_payment': float(p.new_payment),
            'balance': float(p.balance),
            'payment_mode': p.payment_mode,
            'payment_date': p.payment_date.strftime('%d-%m-%Y %I:%M %p'),
        })
    return JsonResponse({'payments': data})

#
def order_view(request):
    return render(request, 'order.html')

def order_list(request):
    query = request.GET.get('q', '')
    status = request.GET.get('status', '')
    date = request.GET.get('date', '')

    orders = Order.objects.all()

    if query:
        orders = orders.filter(
            Q(customer_name__icontains=query) | Q(phone_number__icontains=query)
        )
    if status:
        orders = orders.filter(order_status=status)
    if date:
        orders = orders.filter(date_of_order__date=date)

    paginator = Paginator(orders, 10)  
    page_number = request.GET.get('page')
    orders_page = paginator.get_page(page_number)

    return render(request, 'order.html', {'orders': orders_page})

def order_detail(request, order_id):
    order = get_object_or_404(Order, order_id=order_id)
    paid_now = request.session.pop('paid_now', None)
    return render(request, 'order_detail.html', {'order': order, 'paid_now': paid_now})

def order_success(request):
    return render(request, 'order_success.html')

def create_order(request):
    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            order = form.save()

            item_names = request.POST.getlist('item_name')
            quantities = request.POST.getlist('quantity')
            rates = request.POST.getlist('rate')
            amounts = request.POST.getlist('amount')

            for i in range(len(item_names)):
                if item_names[i] and quantities[i] and rates[i]:
                    OrderItem.objects.create(
                        order=order,
                        item_name=item_names[i],
                        quantity=int(quantities[i]),
                        rate=float(rates[i]),
                        amount=float(amounts[i]),
                    )

            return redirect('order_list')
    else:
        form = OrderForm()
    return render(request, 'order_form.html', {'form': form})

def create_quotation(request):

    if request.method == 'POST':
        try:
            cell = request.POST.get('cell')
            name = request.POST.get('name')           
            address = request.POST.get('address')
            date_joined_raw = (request.POST.get('date_joined') or "").strip()
            date_joined = parse_date(date_joined_raw) if date_joined_raw else None
            if not date_joined:
                date_joined = date.today()
            sale_type = (request.POST.get('sale_type') or "").strip() or "counter"
            bill_type = (request.POST.get('bill_type') or "").strip() or "Credit"
            counter = (request.POST.get('counter') or "").strip()
            if not counter:
                last_log = LoginLog.objects.filter(user=request.user).order_by("-login_time").first()
                raw_computer_name = last_log.computer_name if last_log else ""
                alias_obj = ComputerAlias.objects.filter(computer_name=raw_computer_name).first()
                counter = alias_obj.alias_name if alias_obj else raw_computer_name or "Main Counter"
            total_points = float(request.POST.get('points') or 0)
            earned_points = float(request.POST.get('total_earned') or 0)
            discount = float(request.POST.get('discount') or 0)
            item_data_raw = request.POST.get('item_data')    

            item_data = json.loads(item_data_raw) if item_data_raw else []

            # Auto-generate quotation number
            latest = Quotation.objects.order_by('-id').first()
            base_qtn_no = int(latest.qtn_no) + 1 if latest and str(latest.qtn_no).isdigit() else 1
            qtn_no = str(base_qtn_no)

            # Calculate total before discount
            subtotal = sum(float(item.get('amount', 0)) for item in item_data)
            discount_amount = (subtotal * discount) / 100
            total_after_discount = subtotal - discount_amount

            quotation = Quotation.objects.create(
                qtn_no=qtn_no,
                date=date.today(),
                name=name,                
                address=address,
                cell=cell,
                date_joined=date_joined,
                sale_type=sale_type,
                bill_type=bill_type,
                counter=counter,               
                points=total_points,
                points_earned=earned_points,
                discount=discount,
                items=item_data,
                discount_amt=discount_amount,
                discount_after_total=total_after_discount,
            )

            return JsonResponse({
                'success': True,
                'quotation_id': quotation.id,
                'qtn_no': quotation.qtn_no
            })

        except Exception as e:
            return JsonResponse({'success': False, 'error': f"Failed to save quotation. {str(e)}"})

    # If accessed directly, redirect to the latest quotation (if any)
    last_quotation = Quotation.objects.last()
    if last_quotation:
        return redirect('quotation_detail', qtn_no=last_quotation.qtn_no)
    return redirect('quotation_detail', qtn_no="")

def quotation_detail(request, qtn_no=None):
    # If qtn_no is undefined/empty, fetch the last quotation
    if not qtn_no or qtn_no == "undefined":
        last_quotation = Quotation.objects.last()
        if last_quotation:
            return redirect('quotation_detail', qtn_no=last_quotation.qtn_no)
        else:
            return render(request, 'quotation_detail.html', {'quotation': None, 'qtn_no': None})

    # If qtn_no is provided, fetch that quotation
    try:
        quotation = Quotation.objects.get(qtn_no=qtn_no)
        
        # Handle items (check if already a list or needs JSON parsing)
        if isinstance(quotation.items, list):
            items = quotation.items
        else:
            try:
                items = json.loads(quotation.items) if quotation.items else []
            except (TypeError, json.JSONDecodeError):
                items = []
        
        context = {
            'quotation': quotation,
            'qtn_no': qtn_no,
            'items': items,
            'customer': {
                'name': quotation.name,
                'cell': quotation.cell,               
                'date': quotation.date,
                'sale_type': quotation.sale_type,
            }
        }
        return render(request, 'quotation_detail.html', context)
    
    except Quotation.DoesNotExist:
        return render(request, 'quotation_detail.html', {'quotation': None, 'qtn_no': qtn_no})
    
def get_last_quotation(request):
    last_quotation = Quotation.objects.last()
    
    if not last_quotation:
        return JsonResponse({'error': 'No quotations found'}, status=404)
    
    # Prepare the response data
    data = {
        'qtn_no': last_quotation.qtn_no,
        'date': last_quotation.date.strftime('%Y-%m-%d'),
        'name': last_quotation.name,
        'cell': last_quotation.cell,        
        'address': last_quotation.address,
        'sale_type': last_quotation.sale_type,
        'bill_type': last_quotation.bill_type,
        'counter': last_quotation.counter,
        'points': last_quotation.points,
        'points_earned': last_quotation.points_earned,
        'items': json.loads(last_quotation.items) if last_quotation.items else [],
    }
    
    return JsonResponse(data)
@allow_payments
def update_payment(request, order_id):
    order = get_object_or_404(Order, pk=order_id)

    if request.method == "POST":
        try:
            paid_now_raw = (request.POST.get("paid_now") or "").strip()

            if paid_now_raw:
                normalized = paid_now_raw.replace(",", "")
                if not re.fullmatch(r"\d+(\.\d{1,2})?", normalized):
                    messages.error(request, "Invalid amount. Use up to 2 decimal places.")
                    return redirect('order_detail', order_id=order.order_id)

                paid_now = Decimal(normalized).quantize(Decimal("0.00"), rounding=ROUND_HALF_UP)
                order.paid_amount = paid_now

                total_paid = order.advance + paid_now
                order.due_balance = (order.total_order_amount - total_paid).quantize(Decimal("0.00"), rounding=ROUND_HALF_UP)

            else:
                order.paid_amount = Decimal("0.00")
                order.due_balance = (order.total_order_amount - order.advance).quantize(Decimal("0.00"), rounding=ROUND_HALF_UP)

            order.order_status = 'completed' if order.due_balance <= 0 else 'pending'
            order.save()
            messages.success(request, f"Order #{order_id} payment updated.")

        except Exception as e:
            messages.error(request, f"Error updating payment: {e}")

    return redirect('order_detail', order_id=order.order_id)

def edit_order(request, order_id):
    order = get_object_or_404(Order, order_id=order_id)
    items = order.items.all()

    if request.method == 'POST':
        form = OrderForm(request.POST, instance=order)
        if form.is_valid():
            updated_order = form.save()

            order.items.all().delete()

            item_names = request.POST.getlist('item_name')
            quantities = request.POST.getlist('quantity')
            rates = request.POST.getlist('rate')
            amounts = request.POST.getlist('amount')

            for name, qty, rate, amt in zip(item_names, quantities, rates, amounts):
                OrderItem.objects.create(
                    order=updated_order,
                    item_name=name,
                    quantity=qty,
                    rate=rate,
                    amount=amt
                )

            return redirect('order_detail', order.order_id)
    else:
        form = OrderForm(instance=order)

    context = {
        'form': form,
        'order': order,
        'items': items,
        'editing': True  
    }
    return render(request, 'order_form.html', context)

@transaction.atomic
def convert_quotation_to_order(request, qtn_no):
    quotations = Quotation.objects.filter(qtn_no=qtn_no)
    if not quotations.exists():
        return HttpResponse("Quotation not found")

    first_qtn = quotations.first()

    items = first_qtn.items or []
    advance = float(getattr(first_qtn, 'advance', 0) or 0)
    paid = float(getattr(first_qtn, 'paid', 0) or 0)

    total_amount = sum(float(item.get('amount', 0)) for item in items)
    due = total_amount - (advance + paid)

    bill_no = "1"  

    if first_qtn.bill_no and str(first_qtn.bill_no).strip():
        bill_no = first_qtn.bill_no
    else:
        latest_billing = Billing.objects.order_by('-id').first()
        if latest_billing and latest_billing.bill_no and latest_billing.bill_no.isdigit():
            bill_no = str(int(latest_billing.bill_no) + 1)

    # Create the Order
    order = Order.objects.create(
        customer_name=first_qtn.name,
        phone_number=first_qtn.cell,
        address=first_qtn.address,        
        date_of_order=timezone.now(),
        expected_delivery_datetime=timezone.now(),
        delivery='no',
        charges=0,
        total_order_amount=total_amount,
        advance=advance,
        due_balance=due,
        payment_type='cash',
        order_status='pending', 
        qtn_no=qtn_no,
        bill_no=bill_no,           
    )

    # Create OrderItem records
    for q in quotations:
        for item in (q.items or []):
            rate = float(item.get("sellingprice", 0))
            amount = float(item.get("amount", 0))
            OrderItem.objects.create(
                order=order,
                item_name=item.get("item_name", ""),
                quantity=item.get("qty", 0),
                rate=rate,
                amount=amount,
            )

    # ---- Billing Creation (similar to create_invoice_view) ----
    customer, _ = Customer.objects.get_or_create(
        cell=first_qtn.cell,
        defaults={
            'name': first_qtn.name,            
            'address': first_qtn.address,
        }
    )

    # Generate next bill number
    latest = Billing.objects.order_by('-id').first()
    base_bill_no = int(latest.bill_no) + 1 if latest and str(latest.bill_no).isdigit() else 1
    bill_no = str(base_bill_no)

    # Points
    previous_bill = Billing.objects.filter(customer=customer).order_by('-id').first()
    total_points = previous_bill.points if previous_bill else 0.0
    points_earned_total = 0.0

    # Get values from the first quotation
    bill_type = getattr(first_qtn, 'bill_type', 'order')
    sale_type = getattr(first_qtn, 'sale_type', 'order')
    counter = getattr(first_qtn, 'counter', 'Main Counter')

    billing = Billing.objects.create(
    customer=customer,
    to=customer.name,
    bill_no=bill_no,
    date=timezone.now(),
    bill_type=bill_type,
    counter=counter,
    order_no=order.order_id,
    sale_type=sale_type,
    received=advance + paid,
    balance=due,
    discount=0,
    points=total_points,
    points_earned=0,
    remarks=f"Converted from Quotation {qtn_no}",
    status_on="order_bill",
    created_by=request.user
    )

    # Process stock and Billing Items
    for item in items:
        qty = round(float(item.get("qty", 0)), 2)
        mrp = round(float(item.get("mrsp", 0)), 2)
        selling_price = round(float(item.get("sellingprice", 0)), 2)
        amount = round(qty * selling_price, 2)
        points_earned = round(amount / 200, 2)
        points_earned_total += points_earned

        print(f"\nProcessing Item: {item.get('item_name', '')} | Code: {item.get('code', '')}")
        print(f"Qty: {qty}, MRP: {mrp}, Selling Price: {selling_price}, Amount: {amount}, Points Earned: {points_earned}")

        item_code = item.get("code", "")
        remaining_qty = qty

        inventory_items = Inventory.objects.filter(
            code=item_code,
            quantity__gt=0
        ).order_by('purchased_at', 'id')

        print(f"Found {inventory_items.count()} inventory records for Code: {item_code}")

        for inv_item in inventory_items:
            if remaining_qty <= 0:
                break

            print(f"\nInventory Item ID: {inv_item.id}, Unit: {inv_item.unit}, "
              f"Quantity: {inv_item.quantity}, Split Unit: {inv_item.split_unit}")

            if "bulk" in inv_item.unit.lower():
                available_qty = inv_item.split_unit or 0
                deduct_qty = min(available_qty, remaining_qty)
                unit_quantity = inv_item.unit_qty or 1
                quantity_to_deduct = deduct_qty / unit_quantity
                print(f"Bulk Mode → Available: {available_qty}, Deduct: {deduct_qty}, "
                  f"Unit Qty: {unit_quantity}, Quantity to Deduct: {quantity_to_deduct}")
                inv_item.split_unit = max(0, (inv_item.split_unit or 0) - deduct_qty)
                inv_item.quantity = round(inv_item.quantity - quantity_to_deduct, 1)
            else:
                available_qty = inv_item.quantity
                deduct_qty = min(available_qty, remaining_qty)
                inv_item.quantity -= deduct_qty
                print(f"Normal Mode → Available: {available_qty}, Deduct: {deduct_qty}")

            if ((inv_item.split_unit is None or inv_item.split_unit <= 0) and 
                (inv_item.quantity is None or inv_item.quantity <= 0)):
                inv_item.status = "completed"
                print(f"Inventory Item ID {inv_item.id} marked as completed")

            print(f"After Deduction → Remaining Qty: {remaining_qty}, "
              f"Inventory Qty: {inv_item.quantity}, Split Unit: {inv_item.split_unit}")

            inv_item.save()
            remaining_qty -= deduct_qty

        if remaining_qty > 0:
            print(f"❌ ERROR: Insufficient stock for {item.get('item_name', '')} (Code: {item_code})")
            raise ValueError(f"Insufficient stock for item {item.get('item_name', '')} (Code: {item_code})")
        else:
            print(f" Stock deduction completed for {item.get('item_name', '')} (Code: {item_code})")

        BillingItem.objects.create(
            billing=billing,
            customer=billing.customer,
            code=item_code,
            item_name=item.get("item_name", ""),
            unit=item.get("unit", ""),
            qty=qty,
            mrp=mrp,
            selling_price=selling_price,
            amount=amount
        )

    # Update points in Billing
    billing.points = total_points + points_earned_total
    billing.points_earned = points_earned_total
    billing.save()

    return redirect('order_list')

@allow_items
def item_creation(request):  
    def get_next_item_code(prefix="M", width=3):
        max_num = 0
        codes = Item.objects.filter(code__startswith=prefix).values_list("code", flat=True)
        for code in codes:
            suffix = code[len(prefix):]
            if suffix.isdigit():
                num = int(suffix)
                if num > max_num:
                    max_num = num
        return f"{prefix}{str(max_num + 1).zfill(width)}"

    if request.method == "POST":
        entry_mode = (request.POST.get('code_entry_mode') or 'manual').strip().lower()
        code = (request.POST.get('code') or '').strip()
        if entry_mode == "barcode" and not code:
            messages.error(request, "Please scan the barcode to populate the item code.")
            return redirect('items')
        if not code:
            code = get_next_item_code()
        status = request.POST.get('status')
        item_name = request.POST.get('item_name')
        print_name = request.POST.get('print_name')

        if Item.objects.filter(code=code).exists():
            messages.error(request, f"Item with code '{code}' already exists.")
            return redirect('items')

        # Get tax percent from Tax object
        tax_id = request.POST.get('tax')
        tax_obj = get_object_or_404(Tax, id=tax_id) if tax_id else None
        gst_percent = tax_obj.gst_percent if tax_obj else None

        # Safely fetch ForeignKey instances
        unit_id = request.POST.get('unit')
        P_unit_id = request.POST.get('P_unit')
        group_id = request.POST.get('group')
        brand_id = request.POST.get('brand')        

        unit = get_object_or_404(Unit, id=unit_id) if unit_id else None
        P_unit = get_object_or_404(Unit, id=P_unit_id) if P_unit_id else None
        group = get_object_or_404(Group, id=group_id) if group_id else None
        brand = get_object_or_404(Brand, id=brand_id) if brand_id else None

        unit_name = unit.unit_name if unit else None
        p_unit_name = P_unit.unit_name if P_unit else None
        group_name = group.group_name if group else None
        brand_name = brand.brand_name if brand else None

        HSN_SAC = request.POST.get('hsn_sac')
        use_MRP = request.POST.get('use_mrp') == "Yes"
        points = request.POST.get('points') or 0
        cess_per_qty = request.POST.get('cess_per_qty') or 0

        # Convert numeric fields safely
        P_rate = request.POST.get('p_rate') or 0
        cost_rate = request.POST.get('cost_rate') or 0
        MRSP = request.POST.get('mrp') or 0
        sale_rate = request.POST.get('sale_rate') or 0
        whole_rate = request.POST.get('whole_rate') or 0
        whole_rate_2 = request.POST.get('whole_rate2') or 0
        min_stock = request.POST.get('min_stock') or 0

        barcode = request.POST.get('barcode') or ''
        if not barcode and brand and brand.brand_name.lower() == 'mahil':
            barcode = f"890M{code}"

        gst_percent = 10            

        # Create the item
        Item.objects.create(
            code=code,
            status=status,
            item_name=item_name,
            print_name=print_name,
            unit=unit_name,
            P_unit=p_unit_name,
            group=group_name,
            brand=brand_name,
            tax=gst_percent,
            HSN_SAC=HSN_SAC,
            use_MRP=use_MRP,
            points=points,
            cess_per_qty=cess_per_qty,
            P_rate=P_rate,
            cost_rate=cost_rate,
            MRSP=MRSP,
            sale_rate=sale_rate,
            whole_rate=whole_rate,
            whole_rate_2=whole_rate_2,
            min_stock=min_stock,
            barcode=barcode
        )
        messages.success(request, "Saved successfully!")
        return redirect('items')

    context = {
        'units': Unit.objects.all(),
        'brands': Brand.objects.all(),
        'groups': Group.objects.all(),
        'taxes': Tax.objects.all(),
        'next_item_code': get_next_item_code(),
        'is_edit': False,
        'use_mrp_value': False,
    }
    return render(request, 'items.html', context)

@allow_items
def edit_item(request, item_id):
    item = get_object_or_404(Item, id=item_id)

    if request.method == "POST":
        code = (request.POST.get('code') or '').strip()
        if not code:
            messages.error(request, "Item code is required.")
            return redirect('edit_item', item_id=item_id)

        if Item.objects.filter(code=code).exclude(id=item_id).exists():
            messages.error(request, f"Item with code '{code}' already exists.")
            return redirect('edit_item', item_id=item_id)

        item.code = code
        item.status = request.POST.get('status') or item.status
        item.item_name = request.POST.get('item_name') or item.item_name
        item.print_name = request.POST.get('print_name') or item.print_name

        unit_id = request.POST.get('unit')
        p_unit_id = request.POST.get('P_unit')
        group_id = request.POST.get('group')
        brand_id = request.POST.get('brand')

        if unit_id:
            unit = get_object_or_404(Unit, id=unit_id)
            item.unit = unit.unit_name
        if p_unit_id:
            p_unit = get_object_or_404(Unit, id=p_unit_id)
            item.P_unit = p_unit.unit_name
        if group_id:
            group = get_object_or_404(Group, id=group_id)
            item.group = group.group_name
        if brand_id:
            brand = get_object_or_404(Brand, id=brand_id)
            item.brand = brand.brand_name

        tax_id = request.POST.get('tax')
        if tax_id:
            tax_obj = get_object_or_404(Tax, id=tax_id)
            item.tax = tax_obj.gst_percent

        item.HSN_SAC = request.POST.get('hsn_sac') or item.HSN_SAC
        item.use_MRP = request.POST.get('use_mrp') == "Yes"
        item.points = request.POST.get('points') or 0
        item.cess_per_qty = request.POST.get('cess_per_qty') or 0

        item.P_rate = request.POST.get('p_rate') or 0
        item.cost_rate = request.POST.get('cost_rate') or 0
        item.MRSP = request.POST.get('mrp') or 0
        item.sale_rate = request.POST.get('sale_rate') or 0
        item.whole_rate = request.POST.get('whole_rate') or 0
        item.whole_rate_2 = request.POST.get('whole_rate2') or 0
        item.min_stock = request.POST.get('min_stock') or 0

        item.carry_over = request.POST.get('carry_over') or item.carry_over
        item.manual = request.POST.get('manual') or item.manual
        item.stock_item = request.POST.get('stock_item') or item.stock_item

        item.save()
        messages.success(request, "Item updated successfully!")
        return redirect('items_list')

    units = list(Unit.objects.all())
    groups = list(Group.objects.all())
    brands = list(Brand.objects.all())
    taxes = list(Tax.objects.all())

    selected_unit_id = next((u.id for u in units if str(u) == str(item.unit) or u.unit_name == str(item.unit)), None)
    selected_p_unit_id = next((u.id for u in units if str(u) == str(item.P_unit) or u.unit_name == str(item.P_unit)), None)
    selected_group_id = next((g.id for g in groups if g.group_name == str(item.group)), None)
    selected_brand_id = next((b.id for b in brands if b.brand_name == str(item.brand)), None)
    selected_tax_id = next((t.id for t in taxes if str(t.gst_percent) == str(item.tax)), None)

    use_mrp_value = str(item.use_MRP).lower() in ("yes", "true", "1")

    context = {
        'item': item,
        'units': units,
        'brands': brands,
        'groups': groups,
        'taxes': taxes,
        'selected_unit_id': selected_unit_id,
        'selected_p_unit_id': selected_p_unit_id,
        'selected_group_id': selected_group_id,
        'selected_brand_id': selected_brand_id,
        'selected_tax_id': selected_tax_id,
        'is_edit': True,
        'use_mrp_value': use_mrp_value,
    }
    return render(request, 'items.html', context)
@allow_items
def fetch_item_by_code(request):
    code = request.GET.get('code')
    if not code:
        return JsonResponse({'exists': False})

    try:
        item = Item.objects.get(code=code)
        return JsonResponse({
            'exists': True,
            'item': {
                'item_name': item.item_name,
                'print_name': item.print_name,
                'status': item.status,
                'unit': item.unit.id if item.unit else '',
                'P_unit': item.P_unit.id if item.P_unit else '',
                'group': item.group.id if item.group else '',
                'brand': item.brand.id if item.brand else '',
                'tax_id': item.tax_id if item.tax_id else '',
                'HSN_SAC': item.HSN_SAC,
                'use_MRP': item.use_MRP,
                'points': item.points,
                'cess_per_qty': item.cess_per_qty,
                'P_rate': item.P_rate,
                'cost_rate': item.cost_rate,
                'MRSP': item.MRSP,
                'sale_rate': item.sale_rate,
                'whole_rate': item.whole_rate,
                'whole_rate_2': item.whole_rate_2,
                'min_stock': item.min_stock
            }
        })
    except Item.DoesNotExist:
        return JsonResponse({'exists': False})
    
@allow_items
def items_list(request):
    query_name = request.GET.get('name', '').strip()
    query_code = request.GET.get('code', '').strip()

    items = Item.objects.all().order_by('id')

    if query_name:
        items = items.filter(item_name__icontains=query_name)

    if query_code:
        items = items.filter(code__icontains=query_code)

    context = {
        'items': items,
        'query_name': query_name,
        'query_code': query_code,
    }
    return render(request, 'items_list.html', context) 

@allow_items
def delete_item(request, item_id):
    item = get_object_or_404(Item, id=item_id)

    if request.method == "POST":
        item.delete()
        messages.success(request, f"Item '{item.item_name}' deleted successfully.")
        return redirect('items_list')

    messages.error(request, "Invalid request method.")
    return redirect('items_list')
    
@allow_items  
@csrf_exempt
def check_item_code(request):
    code = request.GET.get("code", "").strip()
    exists = Item.objects.filter(code=code).exists()
    return JsonResponse({"exists": exists})    

from django.shortcuts import render, redirect
from django.contrib import messages
import win32print
import re

def build_label(item, label_size):
    """
    Build label TSPL command based on size.
    """
    # Convert purchased_at from yyyy-mm-dd to dd/mm/yyyy 
    expiry_at_raw = item.get("expiry", "")
    if  expiry_at_raw:
        try:
             dt = datetime.strptime( expiry_at_raw, "%Y-%m-%d")
             expiry_at = dt.strftime("%d/%m/%Y")  # Convert to dd/mm/yyyy
        except ValueError:
             expiry_at =  expiry_at_raw
    else:
         expiry_at = ""

    # Clean barcode for Code39
    barcode_clean = re.sub(r'[^A-Z0-9\-\.\ \$\/\+\%]', '', str(item['barcode']).upper())
    if not barcode_clean:
        barcode_clean = "NA"

    # Size settings (DB sizes take priority)
    size_obj = BarcodeLabelSize.objects.filter(name=label_size).first()
    if size_obj:
        width = size_obj.width_mm
        height = size_obj.height_mm
        per_row = size_obj.per_row or 1
        gap = "3 mm,0 mm"
    else:
        if label_size == "35x22":
            width, height, per_row, gap = 35, 22, 3, "3 mm,0 mm"
        elif label_size == "50x40":
            width, height, per_row, gap = 50, 40, 2, "3 mm,0 mm"
        elif label_size == "70x35":
            width, height, per_row, gap = 70, 35, 1, "3 mm,0 mm"
        else:
            width, height, per_row, gap = 35, 22, 3, "3 mm,0 mm"

    # Base TSPL setup
    tspl = f"SIZE {width*per_row} mm,{height} mm\n"   # total width for row
    tspl += f"GAP {gap}\n"
    tspl += "CLS\n"   # clear buffer

    # Horizontal step per column
    step_x = int(width * 8)  # TSPL uses dots, 1 mm ≈ 8 dots
    base_x, base_y = 20, 20  # adjust text position

    for col in range(per_row):
        offset_x = col * step_x
        tspl += f'TEXT {base_x + offset_x},{base_y + 0},"0",0,10,10,"Mahil SuperMarket"\n'
        tspl += f'TEXT {base_x + offset_x},{base_y + 28},"0",0,10,10,"{item["name"]}"\n'
        tspl += f'TEXT {base_x + offset_x},{base_y + 56},"0",0,9,9,"MRP:{item["mrp"]} Sale:{item["sale"]}"\n'        
        tspl += f'TEXT {base_x + offset_x},{base_y + 84},"0",0,8,8,"{item["code"]}  Exp:{expiry_at}"\n'
        tspl += f'BARCODE {base_x + offset_x},{base_y + 112},"39",40,0,0,1,4,"{barcode_clean}"\n'
    tspl += "PRINT 1\n"
    return tspl    
@allow_barcodes
def print_barcode(request):
    if request.method == "POST":
        label_size = request.POST.get("label_size", "35x22")

        codes = request.POST.getlist("code")
        names = request.POST.getlist("item_name")
        mrps = request.POST.getlist("mrp")
        sales = request.POST.getlist("sale_rate")
        batches = request.POST.getlist("batch_no")
        expirys = request.POST.getlist("expiry_date")
        purchased = request.POST.getlist("purchase_date")
        stickers_qty = request.POST.getlist("stickers")

        items = []
        for i in range(len(codes)):
            try:
                qty = max(int(stickers_qty[i]), 1)
            except (ValueError, TypeError):
                qty = 1

            try:
                item_obj = Item.objects.get(code=codes[i].strip())
                barcode_value = item_obj.barcode
                item_name = item_obj.item_name
            except Item.DoesNotExist:
                barcode_value = codes[i].strip()
                item_name = names[i].strip()

            for _ in range(qty):
                items.append({
                    "code": codes[i].strip(),
                    "name": item_name,
                    "barcode": barcode_value,
                    "mrp": mrps[i].strip(),
                    "sale": sales[i].strip(),
                    "batch": batches[i].strip(),
                    "purchased_at": purchased[i].strip(),
                    "expiry": expirys[i].strip(),                   
                })

            print("Items for printing:")
            for idx, itm in enumerate(items, 1):
                print(f"{idx}: {itm}")

        # Build TSPL code for all labels
        raw_text = ""
        for item in items:
            raw_text += build_label(item, label_size)

        print("----- Generated TSPL Code -----")
        print(raw_text)
        print("----- End TSPL Code -----")

        raw_bytes = raw_text.encode("ascii")

        printer_name = "SNBC TVSE LP 46 NEO BPLE"  # Ensure exact driver name
        try:
            hprinter = win32print.OpenPrinter(printer_name)
            try:
                hjob = win32print.StartDocPrinter(hprinter, 1, ("Label Print Job", None, "RAW"))
                win32print.StartPagePrinter(hprinter)
                win32print.WritePrinter(hprinter, raw_bytes)
                win32print.EndPagePrinter(hprinter)
                win32print.EndDocPrinter(hprinter)
            finally:
                win32print.ClosePrinter(hprinter)

            messages.success(request, "Barcodes printed successfully!")
        except Exception as e:
            messages.error(request, f"Printing failed: {e}")

        return redirect("print_barcode")

    label_sizes = BarcodeLabelSize.objects.all().order_by("name")
    return render(request, "print_barcode.html", {
        "label_sizes": label_sizes,
    })
@allow_barcodes
def fetch_item_details(request):
    code = request.GET.get("code")
    name = request.GET.get("name")

    try:
        # Find Item
        if code:           
            item = Item.objects.filter(code__iexact=code).first()
            if not item:
                item = Item.objects.filter(barcode__iexact=code).first()
        elif name:
            item = Item.objects.get(item_name__iexact=name)
        else:
            return JsonResponse({"error": "No code or name provided"}, status=400)

        # All in-stock batches
        batches = (
            Inventory.objects.filter(item=item, status="in_stock")
            .order_by("-purchased_at")
        )

        if not batches.exists():
            # Item exists but no stock available
            return JsonResponse({
                "code": item.code,
                "item_name": item.item_name,
                "barcode": item.barcode,
                "total_qty": 0,
                "batches": [],
            })

        # Calculate total available quantity
        total_qty = sum(b.quantity for b in batches if b.quantity)

        # Return batch-wise + total info
        batch_list = []
        for b in batches:
            batch_list.append({
                "batch_no": b.batch_no,
                "mrp": float(b.mrp_price) if b.mrp_price else None,
                "sale_rate": float(b.sale_price) if b.sale_price else None,
                "purchased_at": b.purchased_at.strftime("%Y-%m-%d") if b.purchased_at else None,
                "expiry_at": b.expiry_date.strftime("%Y-%m-%d") if b.expiry_date else None,
                "quantity": b.quantity,
            })

        return JsonResponse({
            "code": item.code,
            "item_name": item.item_name,
            "total_qty": total_qty,
            "batches": batch_list,
        })

    except Item.DoesNotExist:
        return JsonResponse({"error": "Item not found"}, status=404)
@allow_barcodes    
def get_itemname1_info(request):
    """
    Return item suggestions with batch information for autocomplete (partial search).
    """
    query = request.GET.get("q", "").strip()
    if not query:
        return JsonResponse({"suggestions": []})

    # Search directly in Inventory.item_name (not item__item_name)
    inventories = (
        Inventory.objects.filter(status="in_stock", item__item_name__icontains=query)
        .order_by("item_name")[:25]
    )

    item_dict = {}
    for inv in inventories:
        code = inv.code  # code is in Inventory table
        if code not in item_dict:
            item_dict[code] = {
                "item_code": inv.item.code,
                "item_name": inv.item.item_name,
                "barcode": inv.item.barcode,
                "unit": inv.unit,
                "total_qty": 0,
                "batches": []
            }

        item_dict[code]["total_qty"] += inv.quantity or 0
        item_dict[code]["batches"].append({
            "batch_no": inv.batch_no,
            "mrp": float(inv.mrp_price) if inv.mrp_price else None,
            "sale_rate": float(inv.sale_price) if inv.sale_price else None,
            "purchased_at": inv.purchased_at.strftime("%Y-%m-%d") if inv.purchased_at else None,
            "expiry_at": inv.expiry_date.strftime("%Y-%m-%d") if inv.expiry_date else None,
            "quantity": inv.quantity,
        })

    return JsonResponse({"suggestions": list(item_dict.values())})

#
def Unit_creation(request):
    if request.method == 'POST':
        unit_name = request.POST.get('unit_name')
        print_name = request.POST.get('print_name')
        decimals_raw = request.POST.get('decimals')
        UQC = request.POST.get('UQC')

        decimals = None if not decimals_raw or decimals_raw.strip() == "" else Decimal(decimals_raw)

        new_unit = Unit.objects.create(
            unit_name=unit_name,
            print_name=print_name,
            decimals=decimals,
            UQC=UQC
        )

        # If AJAX → return JSON
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"success": True, "id": new_unit.id, "name": new_unit.unit_name})

        return_to = request.POST.get("return_to") or request.META.get("HTTP_REFERER")
        if return_to:
            return redirect(return_to)
        return redirect("unit_creation")

    return render(request, 'unit.html')

#
from django.http import JsonResponse
from django.shortcuts import render, redirect
from .models import Group


def Group_creation(request):
    if request.method == "POST":
        try:
            group_name = request.POST.get("group_name", "").strip()
            alias_name = request.POST.get("alias_name", "").strip()
            print_name = request.POST.get("print_name", "").strip()

            # Parent group (can be empty)
            parent_id = request.POST.get("under") or None

            # ===============================
            # VALIDATION
            # ===============================
            if not group_name:
                return JsonResponse(
                    {"success": False, "error": "Group name is required"},
                    status=400
                )

            if Group.objects.filter(group_name__iexact=group_name).exists():
                return JsonResponse(
                    {"success": False, "error": "Group already exists"},
                    status=400
                )

            # ===============================
            # CREATE GROUP (MATCH MODEL)
            # ===============================
            group = Group.objects.create(
                group_name=group_name,
                alias_name=alias_name,
                print_name=print_name,
                parent_id=parent_id  # ✅ CORRECT FIELD
            )

            # ===============================
            # AJAX RESPONSE
            # ===============================
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({
                    "success": True,
                    "id": group.id,
                    "name": group.group_name
                })

            return_to = request.POST.get("return_to") or request.META.get("HTTP_REFERER")
            if return_to:
                return redirect(return_to)
            return redirect("group_creation")

        except Exception as e:
            return JsonResponse(
                {"success": False, "error": str(e)},
                status=500
            )

    return render(request, "group.html")



#
def Brand_creation(request):
    if request.method == 'POST':
        brand_name = request.POST.get('brand_name')
        alias_name = request.POST.get('alias_name')
        under = request.POST.get('under')
        print_name = request.POST.get('print_name')

        brand = Brand.objects.create(
            brand_name=brand_name,
            alias_name=alias_name,
            under=under,
            print_name=print_name,
        )

        #  If AJAX request, return JSON instead of redirect
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({
                "success": True,
                "id": brand.id,
                "name": brand.brand_name
            })

        return_to = request.POST.get("return_to") or request.META.get("HTTP_REFERER")
        if return_to:
            return redirect(return_to)
        return redirect('brand_creation')

    return render(request, 'brand.html')

#
def Tax_creation(request):
    if request.method =='POST':
        tax_name = request.POST.get('tax_name')
        print_name = request.POST.get('print_name')
        tax_type = request.POST.get('tax_type')
        effect_form = request.POST.get('effect_form')
        rounded = int(request.POST.get('rounded'))
        gst_type = request.POST.get('gst_type')
        gst_percent = int(request.POST.get('gst_percent'))
        round_type = request.POST.get('round_type')
        cess_percent = request.POST.get('cess_percent')

        sgst_percent = float(request.POST.get('sgst_percent') or 0)
        sgst_sales_account_1 = request.POST.get('sgst_sales_account_1')
        sgst_sales_account_2 = request.POST.get('sgst_sales_account_2')
        sgst_sales_return_1 = request.POST.get('sgst_sales_return_1')
        sgst_sales_return_2 = request.POST.get('sgst_sales_return_2')

        sgst_purchase_account_1 = request.POST.get('sgst_purchase_account_1')
        sgst_purchase_account_2 = request.POST.get('sgst_purchase_account_2')
        sgst_purchase_return_1 = request.POST.get('sgst_purchase_return_1')
        sgst_purchase_return_2 = request.POST.get('sgst_purchase_return_2')

        cgst_percent = float(request.POST.get('cgst_percent') or 0)
        cgst_sales_account_1 = request.POST.get('cgst_sales_account_1')
        cgst_sales_account_2 = request.POST.get('cgst_sales_account_2')
        cgst_sales_return_1 = request.POST.get('cgst_sales_return_1')
        cgst_sales_return_2 = request.POST.get('cgst_sales_return_2')

        cgst_purchase_account_1 = request.POST.get('cgst_purchase_account_1')
        cgst_purchase_account_2 = request.POST.get('cgst_purchase_account_2')
        cgst_purchase_return_1 = request.POST.get('cgst_purchase_return_1')
        cgst_purchase_return_2 = request.POST.get('cgst_purchase_return_2')

        Tax.objects.create(
            tax_name=tax_name,
            print_name=print_name,
            tax_type=tax_type,
            effect_form=effect_form,
            rounded=rounded,
            gst_type=gst_type,
            gst_percent=gst_percent,
            round_type=round_type,
            cess_percent=cess_percent,
            sgst_percent=sgst_percent,
            sgst_sales_account_1=sgst_sales_account_1,
            sgst_sales_account_2=sgst_sales_account_2,
            sgst_sales_return_1=sgst_sales_return_1,
            sgst_sales_return_2=sgst_sales_return_2,
            sgst_purchase_account_1=sgst_purchase_account_1,
            sgst_purchase_account_2=sgst_purchase_account_2,
            sgst_purchase_return_1=sgst_purchase_return_1,
            sgst_purchase_return_2=sgst_purchase_return_2,
            cgst_percent=cgst_percent,
            cgst_sales_account_1=cgst_sales_account_1,
            cgst_sales_account_2=cgst_sales_account_2,
            cgst_sales_return_1=cgst_sales_return_1,
            cgst_sales_return_2=cgst_sales_return_2,
            cgst_purchase_account_1=cgst_purchase_account_1,
            cgst_purchase_account_2=cgst_purchase_account_2,
            cgst_purchase_return_1=cgst_purchase_return_1,
            cgst_purchase_return_2=cgst_purchase_return_2,
        )
        return redirect('tax_creation')
    return render(request,'tax.html')

@allow_sales_return
def sale_return_view(request):
    billing = None
    billing_items = []
    error = None

    # form-field values to keep inputs sticky
    bill_no = ""
    customer_name = ""
    customer_phone = ""

    # Always compute sale_returns for the page footer/list
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    sale_returns_qs = SaleReturn.objects.select_related('billing', 'customer')

    if start_date and end_date:
        sd = parse_date(start_date)
        ed = parse_date(end_date)
        if sd and ed:
            sale_returns_qs = sale_returns_qs.filter(created_at__date__range=(sd, ed))
    sale_returns_qs = sale_returns_qs.order_by('-created_at')

    # -------------------------
    # Handle POST actions
    # -------------------------
    if request.method == "POST":
        # get sticky values from POST (so template can re-fill inputs)
        bill_no = request.POST.get("bill_no", "").strip()
        customer_name = request.POST.get("customer_name", "").strip()
        customer_phone = request.POST.get("customer_phone", "").strip()

        # DEBUG: log which button was pressed
        # (watch server console when you click Fetch)
        print("POST received. keys:", list(request.POST.keys()))

        # -------- Fetch Bill (no redirect) ----------
        if "fetch_bill" in request.POST:
            print("DEBUG: fetch_bill pressed, bill_no:", bill_no)
            if not bill_no:
                error = "Please enter the Bill Number."
            else:
                billings = Billing.objects.filter(bill_no=bill_no)

                if customer_name:
                    billings = billings.filter(customer__name__icontains=customer_name)

                if customer_phone:
                    billings = billings.filter(customer__cell__icontains=customer_phone)

                if billings.exists():
                    billing = billings.first()
                    billing_items = BillingItem.objects.filter(billing_id=billing.id)
                    print(f"DEBUG: Found billing id={billing.id}, items={billing_items.count()}")
                else:
                    error = "No billing found matching the given criteria."
                    print("DEBUG: No billing found for", bill_no)

        # -------- Process Return ----------
        elif "process_return" in request.POST:
            print("DEBUG: process_return pressed")
            billing_id = request.POST.get("billing_id")
            return_reason = request.POST.get("return_reason", "").strip()

            if not billing_id:
                messages.error(request, "Billing id missing.")
            else:
                billing = get_object_or_404(Billing, id=billing_id)
                billing_items = BillingItem.objects.filter(billing_id=billing.id)

                sale_return = SaleReturn.objects.create(
                    billing=billing,
                    customer=billing.customer,
                    return_reason=return_reason,
                    total_return_qty=Decimal('0.00'),
                    total_refund_amount=Decimal('0.00')
                )

                total_qty = Decimal('0.00')
                total_amount = Decimal('0.00')

                for item in billing_items:
                    ret_qty_str = request.POST.get(f"return_qty_{item.id}", "0")
                    try:
                        ret_qty = Decimal(ret_qty_str)
                    except:
                        ret_qty = Decimal('0.00')

                    if ret_qty > 0:
                        ret_amount = ret_qty * Decimal(str(item.selling_price))

                        SaleReturnItem.objects.create(
                            sale_return=sale_return,
                            billing_item=item,
                            code=item.code,
                            item_name=item.item_name,
                            unit=item.unit,
                            qty=item.qty,
                            mrp=item.mrp,
                            price=item.selling_price,
                            return_qty=ret_qty,
                            return_amount=ret_amount,
                        )

                        # inventory update simplified and defensive
                        try:
                            inventory_item = Inventory.objects.filter(
                                code=item.code,
                                mrp_price=item.mrp,
                                status__iexact="in_stock"
                            ).order_by('-id').first()

                            if inventory_item:
                                if item.unit and "bulk" in str(item.unit).lower():
                                    bag_size = Decimal(str(inventory_item.unit_qty or 1))
                                    qty_fraction = ret_qty / bag_size
                                    inventory_item.quantity += float(qty_fraction)
                                    inventory_item.split_unit = (inventory_item.split_unit or 0) + float(ret_qty)
                                else:
                                    inventory_item.quantity += float(ret_qty)
                                inventory_item.save()
                            else:
                                # try completed or any mrp match or create new
                                completed_item = Inventory.objects.filter(
                                    code=item.code,
                                    mrp_price=item.mrp
                                ).order_by('-id').first()
                                if completed_item:
                                    if item.unit and "bulk" in str(item.unit).lower():
                                        bag_size = Decimal(str(completed_item.unit_qty or 1))
                                        qty_fraction = ret_qty / bag_size
                                        completed_item.quantity += float(qty_fraction)
                                        completed_item.split_unit = (completed_item.split_unit or 0) + float(ret_qty)
                                    else:
                                        completed_item.quantity += float(ret_qty)
                                    completed_item.status = "in_stock"
                                    completed_item.save()
                                else:
                                    Inventory.objects.create(
                                        code=item.code,
                                        item_name=item.item_name,
                                        unit=item.unit,
                                        mrp_price=item.mrp,
                                        quantity=float(ret_qty),
                                        split_unit=float(ret_qty) if item.unit and "bulk" in str(item.unit).lower() else None,
                                        unit_qty=item.unit_qty,
                                        status="in_stock"
                                    )
                        except Exception as e:
                            print("Inventory update error:", e)

                        total_qty += ret_qty
                        total_amount += ret_amount

                sale_return.total_return_qty = total_qty
                sale_return.total_refund_amount = total_amount
                sale_return.save()

                messages.success(request, "Sale return processed successfully.")
                # After processing we redirect to clear POST and show list
                return redirect(reverse('sale_return'))

    # -------------------------
    # GET or fall-through render
    # -------------------------
    context = {
        "billing": billing,
        "billing_items": billing_items,
        "error": error,
        "bill_no": bill_no,
        "customer_name": customer_name,
        "customer_phone": customer_phone,
        "sale_returns": sale_returns_qs,
    }
    return render(request, "sale_return.html", context)



from django.contrib import messages
@allow_sales_return
def sale_return_success_view(request):
    messages.success(request, "Sale return processed successfully.")    
    return redirect('sale_return')
@allow_sales_return
def sale_return_detail(request, pk):
    sale_return = get_object_or_404(SaleReturn, pk=pk)   
    return render(request, 'sale_return_detail.html', {'sale_return': sale_return})
@allow_sales_return
def sale_return_items_api(request):
    sale_return_id = request.GET.get('sale_return_id')
    items_qs = SaleReturnItem.objects.filter(sale_return_id=sale_return_id)
    items = []
    for item in items_qs:
        items.append({
            'code': item.code,
            'item_name': item.item_name,
            'unit': item.unit,
            'qty': item.qty,
            'mrp': float(item.mrp),
            'price': float(item.price),
            'return_qty': item.return_qty,
            'return_amount': float(item.return_amount),
        })
    return JsonResponse({'items': items})


@allow_products
def products_view(request):
    name_query = request.GET.get('name_query', '').strip()
    code_query = request.GET.get('code_query', '').strip()
    selected_group = request.GET.get('group', '').strip()
    page_number = int(request.GET.get("page", 1))

    base_queryset = Item.objects.all()

    # Search by item name
    if name_query:
        base_queryset = base_queryset.filter(item_name__icontains=name_query)

    # Search by item code
    if code_query:
        base_queryset = base_queryset.filter(code__icontains=code_query)

    # Filter by group
    if selected_group:
        base_queryset = base_queryset.filter(group=selected_group)

    # Get unique product IDs by code after filtering
    unique_ids = (
        base_queryset
        .values('code')
        .annotate(min_id=Min('id'))
        .values_list('min_id', flat=True)
    )

    items_queryset = Item.objects.filter(id__in=unique_ids).order_by('id')

    product_count = items_queryset.count()

    # Pagination: 50 per page
    paginator = Paginator(items_queryset, 50)
    page_obj = paginator.get_page(page_number)

    start_index = (page_obj.number - 1) * paginator.per_page

    # For AJAX infinite load
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        html = render_to_string(
            "partials/product_rows.html",
            {"items": page_obj, "start_index": start_index},
            request=request
        )
        return JsonResponse({"html": html, "has_next": page_obj.has_next()})

    groups = Item.objects.values_list('group', flat=True).distinct().order_by('group')

    return render(request, 'products.html', {
        "items": page_obj,
        "name_query": name_query,
        "code_query": code_query,
        "groups": groups,
        "selected_group": selected_group,
        "product_count": product_count,
        "has_next": page_obj.has_next(),
        "start_index": start_index,
    })





# views.py
from django.shortcuts import render, redirect, get_object_or_404
from .models import BarcodeLabelSize
from .forms import BarcodeLabelSizeForm
@allow_barcodes
def label_size_list(request):
    sizes = BarcodeLabelSize.objects.all()
    return render(request, "label_size_list.html", {"sizes": sizes})
@allow_barcodes
def label_size_create(request):
    if request.method == "POST":
        form = BarcodeLabelSizeForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("label_size_list")
    else:
        form = BarcodeLabelSizeForm()
    return render(request, "label_size_form.html", {"form": form})
@allow_barcodes
def label_size_edit(request, pk):
    size = get_object_or_404(BarcodeLabelSize, pk=pk)
    if request.method == "POST":
        form = BarcodeLabelSizeForm(request.POST, instance=size)
        if form.is_valid():
            form.save()
            return redirect("label_size_list")
    else:
        form = BarcodeLabelSizeForm(instance=size)
    return render(request, "label_size_form.html", {"form": form})
@allow_barcodes
def label_size_delete(request, pk):
    size = get_object_or_404(BarcodeLabelSize, pk=pk)
    size.delete()
    return redirect("label_size_list")







@allow_purchase
def purchase_view(request):
    if request.method == 'POST':
        supplier_id = request.POST.get('supplier')
        supplier = get_object_or_404(Supplier, id=supplier_id)
        purchase = Purchase.objects.create(supplier=supplier)

        rows = zip(
            request.POST.getlist('item_code'),
            request.POST.getlist('hsn'),
            request.POST.getlist('qty'),
            request.POST.getlist('price'),
            request.POST.getlist('cost_rate'),
            request.POST.getlist('discount'),
            request.POST.getlist('tax'),
            request.POST.getlist('mrp'),
            request.POST.getlist('whole_price'),
            request.POST.getlist('whole_price1'),
            request.POST.getlist('sale_price'),
        )

        for code, hsn, qty, price, disc, tax, mrp, wp, wp1, sp in rows:
            item = get_object_or_404(Item, code=code)
            qty = float(qty)
            price = float(price)
            discount = float(disc)
            tax = float(tax)

            total = qty * price
            net = total - discount + (total * tax / 100)

            PurchaseItem.objects.create(
                purchase=purchase,
                item=item,  
                hsn=hsn,              
                quantity=qty,
                unit_price=price,
                total_price=total,
                discount=discount,
                tax=tax,
                net_price=net,
                mrp_price=mrp,
                whole_price=wp,
                whole_price_2=wp1,
                sale_price=sp,
            )

        return redirect('purchase_list')

    context = {
        'suppliers': Supplier.objects.all(),
        'items': Item.objects.all(),
    }
    return render(request, 'purchase.html', context)

@allow_purchase
def purchase_list(request):
    supplier_id = request.GET.get('supplier')
    sort_order = request.GET.get('sort', 'desc')
    item_code = request.GET.get('item_code', '').strip()
    item_name = request.GET.get('item_name', '').strip()

    purchases = PurchaseItem.objects.all()

    # Filter by supplier
    if supplier_id == 'None':
        purchases = purchases.filter(Q(supplier_id__isnull=True) | Q(supplier_id=''))
    elif supplier_id:
        purchases = purchases.filter(supplier_id=supplier_id)

    # Apply sort order
    if sort_order == 'asc':
        purchases = purchases.order_by('id')  # Oldest first
    else:
        purchases = purchases.order_by('-id')  # Latest first

    # Filter by item code
    if item_code:
        purchases = purchases.filter(code__icontains=item_code)

    # Filter by item name
    if item_name:
        purchases = purchases.filter(item_name__icontains=item_name)        

    context = {
        'purchases': purchases,
        'supplier_ids': PurchaseItem.objects.values_list('supplier_id', flat=True).distinct(),
        'selected_supplier': supplier_id,
        'sort_order': sort_order,
        'item_code': item_code,
        'item_name': item_name,
    }
    return render(request, 'purchase_list.html', context)
@allow_purchase
def export_purchases(request):
    # Example: return CSV
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="purchases.csv"'
    response.write("id,supplier,amount\n")
    return response

@allow_purchase
def fetch_item(request):
    name = request.GET.get('name', '').strip()
    code = request.GET.get('code', '').strip()

    print(f"Fetching item - Name: '{name}', Code: '{code}'")

    item = None

    if code:
        item = Item.objects.filter(code__iexact=code).first()

    if not item and name:
        item = Item.objects.filter(
            Q(item_name__iexact=name) | Q(code__iexact=name) | Q(barcode__iexact=name)
        ).first()

    if item:
        return JsonResponse({
            'item_name': item.item_name,
            'code': item.code,
            'hsn': item.HSN_SAC or '',
            'group': item.group or '',
            'brand': item.brand or '',
            'unit': item.unit or '',
            'price': item.cost_rate or '',
            'tax': item.tax,
            'wholesale': item.whole_rate,
            'wholesale_1': item.whole_rate_2,
            'sale_price': item.sale_rate,
            'mrp': item.MRSP,           
        })

    return JsonResponse({'error': 'Item not found'}, status=404)

@allow_purchase
@csrf_exempt
def create_purchase(request):
    if request.method != "POST":
        return JsonResponse({'error': 'Invalid method'}, status=405)

    try:    
        supplier_id = request.POST.get("supplier_id")       
        invoice_no = request.POST.get("invoice_no", "").strip()  
        items_data = json.loads(request.POST.get("items", "[]"))
        subtotal = Decimal(request.POST.get("subtotal", 0))
        discount = Decimal(request.POST.get("discount", 0))
        tax = Decimal(request.POST.get("tax", 0))
        total_amount = Decimal(request.POST.get("total", 0))
        amount_paid = Decimal(request.POST.get("amount_paid", 0))
        outstanding_amount = Decimal(request.POST.get("outstanding", 0))
        payment_rate = request.POST.get("payment_rate", "")
        payment_mode = request.POST.get("payment_mode", "")
        payment_ref = request.POST.get("payment_reference", "")

        bill_file = request.FILES.get("bill_attachment")

        supplier = Supplier.objects.get(id=supplier_id)
        total_products = len(items_data)    

        #  Check if invoice already exists
        purchase = Purchase.objects.filter(invoice_no=invoice_no).first()

        # Prevent creating an empty purchase for a new invoice
        if not purchase and len(items_data) == 0:
            return JsonResponse({'error': 'No items to save for a new invoice.'}, status=400)
        if purchase:
            # ---- UPDATE EXISTING PURCHASE ----
            purchase.supplier = supplier
            purchase.total_products = total_products
            purchase.subtotal = subtotal
            purchase.discount = discount
            purchase.tax = tax
            purchase.total_amount = total_amount
            purchase.amount_paid = amount_paid
            purchase.outstanding_amount = outstanding_amount
            purchase.payment_rate = payment_rate
            purchase.payment_mode = payment_mode
            purchase.payment_reference = payment_ref
            if bill_file:
                purchase.bill_attachment = bill_file
            purchase.save()

            def safe_date(value, default=None):
                """Convert input to proper date or None."""
                if not value:  # catches "", None, 0
                    return default
                if isinstance(value, (datetime,)):
                    return value.date()
                if isinstance(value, str):
                    try:
                        return datetime.strptime(value, "%Y-%m-%d").date()
                    except ValueError:
                        return default
                return default

           # TRACK PURCHASEITEM CHANGES                                   
            existing_items = {pi.id: pi for pi in PurchaseItem.objects.filter(purchase=purchase)}

            # 1. UPDATED (all items present in incoming data)
            for data in items_data:
                existing = None
                item_obj = None

                # Try to find existing by ID first
                if data.get("id"):
                    try:
                        existing_id = int(data["id"])
                        existing = existing_items.get(existing_id)
                    except (ValueError, TypeError):
                        existing = None

                # Fallback, find by item_code if not found by ID
                if not existing and data.get("item_code"):
                    existing = next(
                        (pi for pi in existing_items.values() if pi.code == data.get("item_code")), None
                    )

                # Get Item object
                item_obj = Item.objects.filter(code=data.get("item_code")).first() if not existing else existing.item
               
                PurchaseTracking.objects.create(
                    purchase=purchase,
                    item=item_obj,
                    existing_quantity=existing.quantity if existing else 0,
                    updated_quantity=data.get("quantity"),                   
                    total_price=data.get("total_price"),                    
                    whole_price=data.get("whole_price"),
                    whole_price_2=data.get("whole_price_2"),
                    sale_price=data.get("sale_price"),
                    discount=data.get("discount"),
                    net_price=data.get("net_price"),
                    tax=data.get("tax"),
                    supplier=purchase.supplier,                    
                    expiry_date=safe_date(data.get("expiry_date")),
                    purchased_at=safe_date(data.get("purchased_at"), timezone.now()),                    
                    code=data.get("item_code"),
                    item_name=data.get("item_name"),                   
                    hsn=data.get("hsn"),
                    split_unit=data.get("split_unit"),
                    split_unit_price=data.get("split_unit_price"),
                    unit_qty=data.get("unit_qty"),
                    cost_price=data.get("cost_price"),
                    taxable_price=data.get("taxable_price"),
                    status="UPDATED",
                )

            # 2. # REMOVED (items that exist in DB but not in the new request)           
            incoming_ids = [int(i["id"]) for i in items_data if i.get("id")]
            incoming_codes = [i["item_code"] for i in items_data if i.get("item_code")]

            # Existing purchase items in DB
            existing_items = {pi.id: pi for pi in PurchaseItem.objects.filter(purchase=purchase)}

            # REMOVED: only those not present in both ids and codes
            for existing_id, existing in existing_items.items():
                if (existing_id not in incoming_ids) and (existing.code not in incoming_codes):
                    PurchaseTracking.objects.create(
                        purchase=purchase,
                        item=existing.item,
                        existing_quantity=existing.quantity,
                        updated_quantity=0,                       
                        total_price=existing.total_price,                       
                        whole_price=existing.whole_price,
                        whole_price_2=existing.whole_price_2,
                        sale_price=existing.sale_price,
                        discount=existing.discount,
                        net_price=existing.net_price,
                        tax=existing.tax,
                        supplier=purchase.supplier,                       
                        expiry_date=safe_date(existing.expiry_date),
                        purchased_at=safe_date(existing.purchased_at, timezone.now()),                        
                        code=existing.code,
                        item_name=existing.item_name,                        
                        hsn=existing.hsn,
                        split_unit=existing.split_unit,
                        split_unit_price=existing.split_unit_price,
                        unit_qty=existing.unit_qty,
                        cost_price=existing.cost_price,
                        taxable_price=existing.taxable_price,
                        status="REMOVED",
                    )

            # Track incoming (item_id, purchase_id) combos
            incoming_pairs = [
                (Item.objects.filter(code=i.get("item_code")).first().id, purchase.id)
                for i in items_data if i.get("item_code")
            ]

            # Remove deleted purchase items
            incoming_purchaseitem_ids = [i.get("id") for i in items_data if i.get("id")]
            PurchaseItem.objects.filter(purchase=purchase).exclude(id__in=incoming_purchaseitem_ids).delete()

            # Remove deleted inventory items
            Inventory.objects.filter(purchase=purchase).exclude(
                item_id__in=[p[0] for p in incoming_pairs]
            ).delete()           

        else:
            # ---- CREATE NEW PURCHASE ----
            purchase = Purchase.objects.create(
                supplier=supplier,
                invoice_no=invoice_no,
                total_products=total_products,
                subtotal=subtotal,
                discount=discount,
                tax=tax,
                amount_paid=amount_paid,
                total_amount=total_amount,
                outstanding_amount=outstanding_amount,
                payment_rate=payment_rate,
                payment_mode=payment_mode,
                payment_reference=payment_ref,
                bill_attachment=bill_file,                              
            )

        latest_qty_cache = {}       

        for item in items_data:
            item_code = item.get('item_code')
            item_obj = Item.objects.filter(code=item_code).first()
            if not item_obj:
                continue

            qty_purchased = float(item['quantity'])
            item_id = item_obj.id

            # Previous qty for FIFO tracking
            if item_id in latest_qty_cache:
                previous_qty = latest_qty_cache[item_id]
            else:
                last = PurchaseItem.objects.filter(item=item_obj).order_by('-id').first()
                previous_qty = float(last.total_qty) if last else 0
            total_qty = previous_qty + qty_purchased
            latest_qty_cache[item_id] = total_qty

            # Batch number logic
            raw_batch_no = item.get('batch_no', '').strip()
            if not raw_batch_no:
                last_batch = PurchaseItem.objects.filter(code=item_code).exclude(
                    batch_no__isnull=True
                ).exclude(batch_no__exact='').order_by('-id').first()
                if last_batch and last_batch.batch_no.startswith('B'):
                    try:
                        last_num = int(last_batch.batch_no[1:])
                        new_batch_no = f'B{last_num + 1:03d}'
                    except ValueError:
                        new_batch_no = 'B001'
                else:
                    new_batch_no = 'B001'
            else:
                new_batch_no = raw_batch_no

            if item.get("id"):
                # ---- UPDATE EXISTING ROW ----
                purchase_item = PurchaseItem.objects.get(id=item["id"], purchase=purchase)
                purchase_item.quantity = qty_purchased
                purchase_item.unit_qty = item['unit_qty']
                purchase_item.unit_price = item['price']
                purchase_item.split_unit = item['split_unit']
                purchase_item.split_unit_price = item['split_unit_price']
                purchase_item.total_price = item['total_price']
                purchase_item.discount = item['discount']
                purchase_item.tax = item['tax']
                purchase_item.cost_price = item['cost_price']
                purchase_item.net_price = item['net_price']
                purchase_item.mrp_price = item['mrp']
                purchase_item.whole_price = item['whole_price']
                purchase_item.whole_price_2 = item['whole_price_2']
                purchase_item.sale_price = item['sale_price']
                purchase_item.taxable_price = item['taxable_price']
                purchase_item.expiry_date = parse_date(item.get('expiry_date'))
                purchase_item.previous_qty = previous_qty
                purchase_item.total_qty = total_qty
                purchase_item.batch_no = new_batch_no
                purchase_item.save()               

            else:
                # ---- ADD NEW ROW ----
                purchase_item = PurchaseItem.objects.create(
                    purchase=purchase,
                    item=item_obj,
                    group=item_obj.group,
                    brand=item_obj.brand,
                    unit=item_obj.unit,
                    code=item.get('item_code', ''),
                    item_name=item.get('item_name', ''),
                    hsn=item.get('hsn'),
                    quantity=qty_purchased,
                    unit_qty=item['unit_qty'],
                    unit_price=item['price'],
                    split_unit=item['split_unit'],
                    split_unit_price=item['split_unit_price'],
                    total_price=item['total_price'],
                    discount=item['discount'],
                    taxable_price=item['taxable_price'],
                    tax=item['tax'],
                    cost_price=item['cost_price'],
                    net_price=item['net_price'],
                    mrp_price=item['mrp'],
                    whole_price=item['whole_price'],
                    whole_price_2=item['whole_price_2'],
                    sale_price=item['sale_price'],
                    supplier_id=supplier.supplier_id,
                    purchased_at=now().date(),
                    batch_no=new_batch_no,
                    expiry_date=parse_date(item.get('expiry_date')),
                    previous_qty=previous_qty,
                    total_qty=total_qty
                )

            inv = Inventory.objects.filter(purchase=purchase, item=item_obj).first()
            if inv:
                #  Update existing inventory
                inv.quantity = qty_purchased
                inv.unit_qty = item['unit_qty']
                inv.unit_price = item['price']
                inv.split_unit = item['split_unit']
                inv.split_unit_price = item['split_unit_price']
                inv.total_price = item['total_price']
                inv.discount = item['discount']
                inv.tax = item['tax']
                inv.cost_price = item['cost_price']
                inv.net_price = item['net_price']
                inv.mrp_price = item['mrp']
                inv.whole_price = item['whole_price']
                inv.whole_price_2 = item['whole_price_2']
                inv.sale_price = item['sale_price']
                inv.taxable_price = item['taxable_price']
                inv.expiry_date = parse_date(item.get('expiry_date'))
                inv.previous_qty = previous_qty
                inv.total_qty = total_qty
                inv.batch_no = new_batch_no
                inv.save()
            else:
                #  Create new inventory if missing
                Inventory.objects.create(
                    item=item_obj,
                    item_name=item.get('item_name', ''),
                    code=item.get('item_code', ''),
                    hsn=item.get('hsn'),
                    group=item_obj.group,
                    brand=item_obj.brand,
                    unit=item_obj.unit,
                    batch_no=new_batch_no,
                    supplier=supplier,
                    quantity=qty_purchased,
                    previous_qty=previous_qty,
                    total_qty=total_qty,
                    unit_qty=item['unit_qty'],
                    unit_price=item['price'],
                    split_unit=item['split_unit'],
                    split_unit_price=item['split_unit_price'],
                    total_price=item['total_price'],
                    discount=item['discount'],
                    tax=item['tax'],
                    cost_price=item['cost_price'],
                    net_price=item['net_price'],
                    mrp_price=item['mrp'],
                    whole_price=item['whole_price'],
                    whole_price_2=item['whole_price_2'],
                    sale_price=item['sale_price'],
                    taxable_price=item['taxable_price'],
                    purchased_at=now().date(),
                    expiry_date=parse_date(item.get('expiry_date')),
                    purchase=purchase
                )

         # Calculate running totals
        previous_total_paid = purchase.payments.aggregate(total_paid=models.Sum('payment_amount'))['total_paid'] or 0
        payment_amount = amount_paid - previous_total_paid
        total_payment_amount = previous_total_paid + payment_amount
        balance_amount = total_amount - total_payment_amount

        # Create a new payment record
        PurchasePayment.objects.create(
            purchase=purchase,
            supplier=purchase.supplier,
            invoice_no=purchase.invoice_no,
            payment_date=now().date(),
            payment_amount=payment_amount,
            payment_mode=payment_mode,
            payment_reference=payment_ref,
            total_amount=total_amount,
            balance_amount=balance_amount
        )    
              
        return JsonResponse({'success': True, 'purchase_id': purchase.id})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@allow_purchase
def fetch_purchase_items(request):
    invoice_number = request.GET.get('invoice_number')    

    if not invoice_number:
        return JsonResponse({'error': 'Invoice number is required'}, status=400)

    try:
        purchase = Purchase.objects.get(invoice_no=invoice_number)
    except Purchase.DoesNotExist:
        return JsonResponse({'error': 'New Invoice number added'}, status=404)

    items = PurchaseItem.objects.filter(purchase_id=purchase.id)
    items_data = []

    for item in items:
        items_data.append({
            'item_name': item.item_name,
            'item_code': item.code,
            'hsn': item.hsn,
            'unit': item.unit,
            'quantity': item.quantity,
            'unit_qty': item.unit_qty,
            'split_unit': item.split_unit,
            'split_unit_price': item.split_unit_price,
            'price': item.unit_price,
            'total_price': item.total_price,
            'discount': item.discount,
            'tax': item.tax,
            'cost_price': item.cost_price,
            'net_price': item.net_price,
            'taxable_price': item.taxable_price,
            'mrp': item.mrp_price,
            'whole_price': item.whole_price,
            'whole_price_2': item.whole_price_2,
            'sale_price': item.sale_price,
            'expiry_date': item.expiry_date,
        })

    purchase_data = {
        'amount_paid': str(purchase.amount_paid or 0),
        'outstanding_amount': str(purchase.outstanding_amount or 0),
        'payment_mode': purchase.payment_mode or "",
        'payment_rate': str(purchase.payment_rate or 0),
        'payment_reference': purchase.payment_reference or "",
    }

    print("Returning", len(items_data), "items for invoice:", invoice_number)
    return JsonResponse({'items': items_data, 'purchase': purchase_data})
@allow_purchase
def daily_purchase_payment_view(request):
    if request.method == "POST":       
        
        supplier_id = request.POST.get('supplierName')
        supplier = Supplier.objects.get(id=supplier_id)
        invoice_no = request.POST.get('invoice_number')
        total_purchase_amount = float(request.POST.get('totalPurchaseAmount'))
        amount_paid = float(request.POST.get('amountPaid'))
        balance = float(request.POST.get('balance'))
        payment_mode = request.POST.get('paymentMode')
        payment_rate_str = request.POST.get('paymentRate')
                
        payment_rate = float(payment_rate_str.replace('%', '')) if payment_rate_str else 0.0           

        # Create a new DailyPurchasePayment record
        payment_record = DailyPurchasePayment(
            supplier=supplier,
            invoice_no=invoice_no,
            total_purchase_amount=total_purchase_amount,
            amount_paid=amount_paid,
            balance=balance,
            payment_mode=payment_mode,
            payment_rate=payment_rate           
        )
       
        payment_record.save()
      
        return redirect('daily_purchase_payment')
  
    suppliers = Supplier.objects.all()
    return render(request, 'daily_purchase_payment.html', {"suppliers": suppliers})
@allow_purchase
def get_invoice_details(request):
    invoice_no = request.GET.get("invoice_no", "").strip()
    data = {
        "total_purchase_amount": 0, 
        "balance": 0
    }

    if invoice_no:
        payment = DailyPurchasePayment.objects.filter(invoice_no=invoice_no).order_by('-created_at').first()
        if payment:
            data = {
                "total_purchase_amount": payment.total_purchase_amount,       
                "balance": payment.balance
            }

    return JsonResponse(data)
@allow_purchase
def purchase_payment_list_view(request):
    payments = DailyPurchasePayment.objects.select_related('supplier').order_by('-created_at')

    # Get filter parameters from GET request
    start_date = (request.GET.get('start_date') or "").strip()
    end_date = (request.GET.get('end_date') or "").strip()
    supplier_name = (request.GET.get('supplier_name') or "").strip()
    invoice_no = (request.GET.get('invoice_no') or "").strip()

    # Date range filter (only if provided)
    if start_date:
        try:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            payments = payments.filter(created_at__date__gte=start_date_obj)
        except ValueError:
            pass

    if end_date:
        try:
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            payments = payments.filter(created_at__date__lte=end_date_obj)
        except ValueError:
            pass

    # Supplier filter
    if supplier_name:
        payments = payments.filter(supplier__name__icontains=supplier_name)

    # Invoice number filter
    if invoice_no:
        payments = payments.filter(invoice_no__icontains=invoice_no)

    # Calculate totals only on filtered results
    total_amount_paid = payments.aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0
    total_purchase_amount = (payments.values('invoice_no').distinct().aggregate(total=Sum('total_purchase_amount'))['total'] or 0)
    latest_payment = payments.order_by('-created_at').first()   
    total_balance = latest_payment.balance if latest_payment else 0      

    # Calculate payment rate
    if total_purchase_amount > 0:
        payment_rate = (total_amount_paid / total_purchase_amount) * 100
    else:
        payment_rate = 0

    print("Payments", payments)

    return render(request, 'purchase_payment_list.html', {
        'payments': payments,
        'total_amount_paid': total_amount_paid,
        'total_purchase_amount': total_purchase_amount,
        'total_balance': total_balance,
        'payment_rate': payment_rate,
        'start_date': start_date,
        'end_date': end_date
    })
@allow_purchase
@never_cache
def purchase_tracking(request):  
    purchase_tracking_summary = PurchaseTracking.objects.select_related(
        'purchase', 'purchase__supplier'
    ).order_by('-tracked_at')

    # Get filter values from GET parameters
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    supplier_code = request.GET.get('supplier_code')
    invoice_no = request.GET.get('invoice_no')

    # Apply filters if provided
    if start_date:
        purchase_tracking_summary = purchase_tracking_summary.filter(tracked_at__date__gte=start_date)
    if end_date:
        purchase_tracking_summary = purchase_tracking_summary.filter(tracked_at__date__lte=end_date)
    if supplier_code:
        purchase_tracking_summary = purchase_tracking_summary.filter(
            purchase__supplier__supplier_id__icontains=supplier_code
        )
    if invoice_no:
        purchase_tracking_summary = purchase_tracking_summary.filter(
            purchase__invoice_no__icontains=invoice_no
        )

    return render(request, 'purchase_update_tracking.html', {
        'purchase_tracking_summary': purchase_tracking_summary
    })

@allow_purchase
def purchase_page(request):
    return render(request, "purchase.html")

@allow_inventory
@csrf_exempt
def stock_adjustment_view(request):
    # Get latest item ID for each code
    latest_by_code = (
        PurchaseItem.objects
        .filter(code__isnull=False)
        .values('code')
        .annotate(latest_id=Max('id'))
    )

    # Then fetch those rows
    unique_products = PurchaseItem.objects.filter(id__in=[entry['latest_id'] for entry in latest_by_code])
    
    # All products with batch info
    products = PurchaseItem.objects.filter(item_name__isnull=False)

    if request.method == "POST":
        product_id = request.POST.get("product")
        adjustment_type = request.POST.get("adjustmentType")
        quantity = request.POST.get("quantity")        
        split_quantity = request.POST.get("split_quantity")
        reason = request.POST.get("reason")
        remarks = request.POST.get("remarks")

        print("DEBUG: Received POST Data")
        print("Product ID:", product_id)
        print("Adjustment Type:", adjustment_type)
        print("Quantity:", quantity)
        print("Split Quantity:", split_quantity)
        print("Reason:", reason)
        print("Remarks:", remarks)


        split_quantity = Decimal(split_quantity or "0")

        # Validate required fields
        if not all([product_id, adjustment_type, quantity, split_quantity]):
            messages.error(request, "All required fields must be filled.")
            return redirect('stock_adjustment')

        # Validate quantity
        try:
            quantity = Decimal(quantity)
            if quantity <= 0:
                messages.error(request, "Quantity must be greater than 0.")
                return redirect('stock_adjustment')
        except InvalidOperation:
            messages.error(request, "Invalid quantity format.")
            return redirect('stock_adjustment')

        # Get the selected batch and item
        selected_batch = get_object_or_404(PurchaseItem, id=product_id)
        item = selected_batch.item

        # Get all batches of the same item
        all_batches = PurchaseItem.objects.filter(item=item).order_by('purchased_at', 'id')

        if adjustment_type == "add":
            selected_batch.quantity += quantity      
            selected_batch.save()

            selected_batch.total_price = selected_batch.quantity * selected_batch.cost_price
            selected_batch.net_price = selected_batch.total_price - (selected_batch.discount or 0)
            selected_batch.save()

        elif adjustment_type == "subtract":
            total_available = sum(b.quantity for b in all_batches)
            if total_available < quantity:
                messages.error(request, f"Insufficient total stock. Available: {total_available}")
                return redirect('stock_adjustment')

            remaining = quantity

            # Subtract from selected batch first, then others if needed
            ordered_batches = [selected_batch] + list(all_batches.exclude(id=selected_batch.id))

            for batch in ordered_batches:
                if remaining <= 0:
                    break

                if batch.quantity >= remaining:
                    batch.quantity -= remaining
                    batch.save()
                    remaining = Decimal("0")
                else:
                    remaining -= batch.quantity
                    batch.quantity = Decimal("0")
                    batch.save()

            for batch in ordered_batches:
                batch.total_price = batch.quantity * batch.cost_price
                batch.net_price = batch.total_price - (batch.discount or 0)
                batch.save()

        else:
            messages.error(request, "Invalid adjustment type.")
            return redirect('stock_adjustment')   
        
        purchase = selected_batch.purchase

        print("Quantity 1:", quantity)
        print("Split Quantity 1:", split_quantity)

        StockAdjustment.objects.create(
            purchase=purchase,
            invoice_no=purchase.invoice_no,
            purchase_item=selected_batch,       
            batch_no=selected_batch.batch_no,
            code=selected_batch.code,
            item_name=selected_batch.item_name, 
            unit=selected_batch.unit, 
            unit_price=selected_batch.unit_price, 
            cost_price=selected_batch.cost_price,        
            supplier_code=selected_batch.purchase.supplier.supplier_id,          
            adjustment_type=adjustment_type,
            quantity=quantity,     
            split_unit=split_quantity,       
            adjusted_net_price=quantity * selected_batch.unit_price,
            reason=reason,
            remarks=remarks,                    
        )

        # Recalculate `previous_qty` and `total_qty` for all batches of this item
        cumulative_total = Decimal("0.00")
        for batch in PurchaseItem.objects.filter(item=item).order_by('purchased_at', 'id'):
            batch.previous_qty = cumulative_total
            batch.total_qty = cumulative_total + batch.quantity
            batch.save()
            cumulative_total = batch.total_qty

        try:
            # Find the specific inventory row for the same batch and item code
            inventory_record = Inventory.objects.get(
                code=selected_batch.code,
                batch_no=selected_batch.batch_no
            )

            # Recalculate the batch-specific quantity
            inv_qty = Decimal(inventory_record.quantity or 0)

            if adjustment_type == "add":
                inv_qty += quantity
            elif adjustment_type == "subtract":
                inv_qty -= quantity
                if inv_qty < 0:
                    inv_qty = Decimal(0)

            inventory_record.quantity = float(inv_qty)

            unit = selected_batch.unit.strip().lower()

            # Update split_unit first if bulk
            if "bulk" in unit:
                if adjustment_type == "add":
                    inventory_record.split_unit = (inventory_record.split_unit or 0) + float(split_quantity)
                elif adjustment_type == "subtract":
                    inventory_record.split_unit = max(0.0, (inventory_record.split_unit or 0) - float(split_quantity))

                # Status based on split_unit for bulk
                if inventory_record.split_unit > 0:
                    inventory_record.status = "in_stock"
                else:
                    inventory_record.status = "completed"
            else:
                # Status based on quantity for non-bulk
                if inventory_record.quantity > 0:
                    inventory_record.status = "in_stock"
                else:
                    inventory_record.status = "completed"

            # Update pricing
            inventory_record.total_price = inventory_record.quantity * float(selected_batch.cost_price)
            inventory_record.net_price = inventory_record.total_price - float(selected_batch.discount or 0)

            inventory_record.save()                    

            print("Split quantity before update:", split_quantity)
            print("Inventory split_unit before update:", inventory_record.split_unit)

            print("Quantity:", quantity)
            print("Split Quantity:", split_quantity)

        except Inventory.DoesNotExist:
            # Create a new inventory record for this batch
            Inventory.objects.create(
                code=selected_batch.code,
                item=selected_batch.item,
                item_name=selected_batch.item_name,
                quantity=quantity if adjustment_type == 'add' else 0,
                split_unit=float(split_quantity) if adjustment_type == 'add' else 0,
                sale_price=selected_batch.sale_price,
                brand=selected_batch.brand,
                group=selected_batch.group,
                unit=selected_batch.unit,
                hsn=selected_batch.hsn,
                supplier=selected_batch.purchase.supplier,
                purchased_at=selected_batch.purchased_at,
                batch_no=selected_batch.batch_no,
                total_price=quantity * selected_batch.cost_price if adjustment_type == 'add' else 0,
                net_price=(quantity * selected_batch.cost_price - (selected_batch.discount or 0)) if adjustment_type == 'add' else 0
            )            

        messages.success(
            request,
            f"Stock successfully adjusted: {adjustment_type.upper()} {quantity} units for '{selected_batch.item_name}' (Batch {selected_batch.batch_no})."
        )
        return redirect('stock_adjustment')

    return render(request, "stock_adjustment.html", {
        "products": products,
        "unique_products": unique_products
    })

@allow_inventory
def stock_adjustment_list(request):
    adjustments = StockAdjustment.objects.all()

    code = request.GET.get('code')
    invoice_no = request.GET.get('invoice_no')
    item_name = request.GET.get('item_name')
    supplier_code = request.GET.get('supplier_code')
    batch_no = request.GET.get('batch_no')

    if code:
        adjustments = adjustments.filter(code__icontains=code)
    if invoice_no:
        adjustments = adjustments.filter(invoice_no__icontains=invoice_no)
    if item_name:
        adjustments = adjustments.filter(item_name__icontains=item_name)
    if supplier_code:
        adjustments = adjustments.filter(supplier_code__icontains=supplier_code)
    if batch_no:
        adjustments = adjustments.filter(batch_no__icontains=batch_no)

    # Order by most recent adjustment
    adjustments = adjustments.order_by('-adjusted_at')

    return render(request, 'stock_adjustment_list.html', {
        'adjustments': adjustments,
        'filters': {
            'code': code or '',
            'invoice_no': invoice_no or '',
            'item_name': item_name or '',
            'supplier_code': supplier_code or '',
            'batch_no': batch_no or '',
        }
    })

@allow_inventory
def edit_bulk_item(request, item_id):
    bulk_item = get_object_or_404(Inventory, id=item_id)

    print("Original bulk_item:", bulk_item.id)
    supplier_id = bulk_item.supplier_id
    purchase_id = bulk_item.purchase_id  

    if request.method == 'POST':
        print("POST request received:", request.POST)

        original_split_unit = float(bulk_item.split_unit or 0)       
        posted_split_qty = float(request.POST.get('split_quantity') or 0)
        updated_split_unit = original_split_unit - posted_split_qty
        bulk_item.split_unit = updated_split_unit
        bulk_item.save(update_fields=['split_unit'])           

        try:
            item_code = request.POST.get('code')
            try:
                item_obj = Item.objects.get(code=item_code)
            except Item.DoesNotExist:
                messages.error(request, f"No item found with code '{item_code}'")
                return redirect(request.path)

            inventory = Inventory(
                item=item_obj,
                item_name=request.POST.get('item_name'),
                code=item_code,
                group=request.POST.get('group'),
                brand=request.POST.get('brand'),
                unit=request.POST.get('unit'),
                batch_no=request.POST.get('batch_no'),
                quantity=float(request.POST.get('quantity') or 0),
                split_unit=float(request.POST.get('split_quantity') or 0),
                previous_qty=float(request.POST.get('previous_qty') or 0),
                total_qty=float(request.POST.get('total_qty') or 0),
                unit_price=float(request.POST.get('unit_price') or 0),
                total_price=float(request.POST.get('total_price') or 0),
                discount=float(request.POST.get('discount') or 0),
                tax=float(request.POST.get('tax') or 0),
                cost_price=float(request.POST.get('cost_price') or 0),
                net_price=float(request.POST.get('net_price') or 0),
                mrp_price=float(request.POST.get('mrp_price') or 0),
                whole_price=float(request.POST.get('whole_price') or 0),
                whole_price_2=float(request.POST.get('whole_price_2') or 0),
                sale_price=float(request.POST.get('sale_price') or 0),
                purchased_at=now(),  # timezone-aware
                expiry_date=request.POST.get('expiry_date'),
                supplier_id=supplier_id,
                purchase_id=purchase_id,
                created_at=now(),
                remarks=request.POST.get('remarks'),
            )
            inventory.save()
            print("Inventory saved with ID:", inventory.id)

            messages.success(request, "Item added to inventory successfully.")
            return redirect('split_stock')

        except Exception as e:
            print("Save error:", e)
            messages.error(request, f"Error saving to inventory: {e}")

    return render(request, 'edit_bulk_item.html', {'item': bulk_item})

@allow_inventory
def fetch_item_info(request):
    code = request.GET.get('code')
    name = request.GET.get('name')
    
    item = None
    if code:
        item = Item.objects.filter(code__iexact=code).first()
    elif name:
        item = Item.objects.filter(item_name__iexact=name).first()

    if item:
        return JsonResponse({
            'item_id': item.id,
            'item_name': item.item_name,
            'code': item.code,
            'group': item.group,
            'brand': item.brand,
            'unit': item.unit,
            'unit_price': float(item.cost_rate),
            'mrp_price': float(item.MRSP),
            'whole_price': float(item.whole_rate),
            'whole_price_2': float(item.whole_rate_2),
            'sale_price': float(item.sale_rate),
        })
    
    return JsonResponse({'error': 'Item not found'}, status=404)
# keep your decorator
# views.py
from django.shortcuts import render
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.template.loader import render_to_string

# Adjust imports to your project structure
from .models import Inventory
from .decorators import allow_inventory

@allow_inventory
def inventory_view(request):
    query = request.GET.get('q', '').strip()
    page_number = int(request.GET.get('page', 1))

    # Base queryset: exclude units containing 'bulk', only positive quantity, newest first
    qs = Inventory.objects.select_related('item') \
        .exclude(item__unit__icontains='bulk') \
        .filter(quantity__gt=0) \
        .order_by('-id')

    if query:
        qs = qs.filter(
            Q(item__item_name__icontains=query) |
            Q(item__code__icontains=query) |
            Q(item__barcode__icontains=query) |
            Q(item__brand__icontains=query) |
            Q(item__unit__icontains=query)
        )

    paginator = Paginator(qs, 50)  # 50 products per page
    page_obj = paginator.get_page(page_number)

    # start_index for continuous S no (0-based offset)
    start_index = (page_obj.number - 1) * paginator.per_page

    # If AJAX (infinite scroll) request -> return rendered rows and has_next
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        html = render_to_string(
            "partials/inventory_rows.html",
            {"items": page_obj, "start_index": start_index},
            request=request
        )
        return JsonResponse({"html": html, "has_next": page_obj.has_next()})

    # Normal render
    return render(request, "inventory.html", {
        "items": page_obj,
        "has_next": page_obj.has_next(),
        "start_index": start_index,
        "query": query
    })


@allow_inventory
def split_stock_page(request):
    queryset = Inventory.objects.filter(unit__icontains='bulk', split_unit__gt=0)

    batch_no = request.GET.get('batch_no', '').strip()
    purchased_at = request.GET.get('purchased_at', '').strip()
    item_name = request.GET.get('item_name', '').strip()
    code = request.GET.get('code', '').strip()
    brand = request.GET.get('brand', '').strip()

    if batch_no:
        queryset = queryset.filter(batch_no__icontains=batch_no)
    if purchased_at:
        queryset = queryset.filter(purchased_at=purchased_at)
    if item_name:
        queryset = queryset.filter(item_name__icontains=item_name)
    if code:
        queryset = queryset.filter(code__icontains=code)
    if brand:
        queryset = queryset.filter(brand__icontains=brand)

    bulk_items = queryset.order_by('-id')  # Ensure this comes after filters

    filters = {
        'batch_no': batch_no,
        'purchased_at': purchased_at,
        'item_name': item_name,
        'code': code,
        'brand': brand,
    }

    return render(request, 'split_stock.html', {
        'bulk_items': bulk_items,
        'filters': filters,
    })

@allow_products
def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    return render(request, 'product_detail.html', {'product': product})

@allow_suppliers
def suppliers_view(request):
    search_query = request.GET.get('q', '')
    suppliers = Supplier.objects.all()
    
    if search_query:
        suppliers = suppliers.filter(
            Q(name__icontains=search_query) |
            Q(contact_person__icontains=search_query) |
            Q(phone__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(address__icontains=search_query) |    
            Q(supplier_id__icontains=search_query)
        )
    
    form = SupplierForm()

    if request.method == 'POST':
        form = SupplierForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('suppliers')

    return render(request, 'suppliers.html', {
        'suppliers': suppliers,
        'form': form,
    })

from django.shortcuts import render, redirect, get_object_or_404
from MahilMartPOS_App.models import Supplier


def get_next_supplier_id_preview():
    last_supplier = Supplier.objects.order_by('-id').first()
    if last_supplier and last_supplier.supplier_id:
        last_number = int(last_supplier.supplier_id.split('-')[1])
        next_number = last_number + 1
    else:
        next_number = 1
    return f"SUP-{next_number:04d}"


@allow_suppliers
def add_supplier(request):
    if request.method == "POST":
        Supplier.objects.create(
            name=request.POST.get("name"),
            contact_person=request.POST.get("contact_person"),
            phone=request.POST.get("phone"),
            email=request.POST.get("email"),
            address=request.POST.get("address"),
            gst_number=request.POST.get("gst_number"),
            fssai_number=request.POST.get("fssai_number"),
            pan_number=request.POST.get("pan_number"),
            credit_terms=request.POST.get("credit_terms"),
            opening_balance=request.POST.get("opening_balance") or 0,
            bank_name=request.POST.get("bank_name"),
            account_number=request.POST.get("account_number"),
            ifsc_code=request.POST.get("ifsc_code"),
            status=request.POST.get("status") or "Active",
            notes=request.POST.get("notes"),
        )
        return redirect("suppliers")

    return render(request, "add_supplier.html", {
        "next_supplier_id": get_next_supplier_id_preview()
    })


@allow_suppliers
def edit_supplier(request, supplier_id):
    supplier = get_object_or_404(Supplier, pk=supplier_id)

    if request.method == "POST":
        # ❌ DO NOT TOUCH supplier_id
        supplier.name = request.POST.get("name")
        supplier.contact_person = request.POST.get("contact_person")
        supplier.phone = request.POST.get("phone")
        supplier.email = request.POST.get("email")
        supplier.address = request.POST.get("address")
        supplier.gst_number = request.POST.get("gst_number")
        supplier.fssai_number = request.POST.get("fssai_number")
        supplier.pan_number = request.POST.get("pan_number")
        supplier.credit_terms = request.POST.get("credit_terms")
        supplier.opening_balance = request.POST.get("opening_balance") or 0
        supplier.bank_name = request.POST.get("bank_name")
        supplier.account_number = request.POST.get("account_number")
        supplier.ifsc_code = request.POST.get("ifsc_code")
        supplier.status = request.POST.get("status")
        supplier.notes = request.POST.get("notes")
        supplier.save()

        return redirect("suppliers")

    return render(request, "edit_supplier.html", {
        "supplier": supplier
    })


@allow_suppliers
def delete_supplier(request, supplier_id):
    supplier = get_object_or_404(Supplier, pk=supplier_id)
    supplier.delete()
    return redirect('suppliers')

from django.contrib.auth.decorators import login_required, user_passes_test

@allow_customers
def customers_view(request):
    try:
        start_date = request.GET.get("start")
        end_date = request.GET.get("end")
        phone = request.GET.get("phone")

        # Base QuerySets
        manual_qs = Customer.objects.filter(remarks="manual_entry")
        billing_qs = Customer.objects.filter(remarks="billing_entry")

        # Apply Date Filter
        if start_date and end_date:
            manual_qs = manual_qs.filter(date_joined__date__range=[start_date, end_date])
            billing_qs = billing_qs.filter(date_joined__date__range=[start_date, end_date])

        if phone:
            manual_qs = manual_qs.filter(cell__icontains=phone)
            billing_qs = billing_qs.filter(cell__icontains=phone)            

        # Customers from Customer table (manual entries)
        customer_entries = manual_qs.order_by("-date_joined")

        # Customers from Billing table (unique by phone, grouped)
        billing_customers = (
            billing_qs            
            .values("id", "name", "cell", "address", "email")
            .annotate(date_joined=Min("date_joined"))
            .order_by("-date_joined")
        )

        # Counts (based on filter if applied)
        total_customers = manual_qs.count() + billing_qs.count()
        total_manual_customers = manual_qs.count()
        total_billing_customers = billing_customers.count()

    except Exception as e:
        from django.http import HttpResponse
        return HttpResponse("Error: " + str(e))

    return render(request, "customers.html", {
        "customer_entries": customer_entries,
        "billing_customers": billing_customers,
        "total_customers": total_customers,
        "total_manual_customers": total_manual_customers,
        "total_billing_customers": total_billing_customers,
        "start_date": start_date,
        "end_date": end_date,
        "phone": phone,
    })
 
@allow_customers
def add_customer(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        cell = request.POST.get('phone')
        address = request.POST.get('address')
        email = request.POST.get('email')

        if Customer.objects.filter(cell=cell).exists():
            messages.error(request, f"Customer with phone {cell} already exists! or Empty values, Please enter on the alternate number")
            return render(request, 'add_customer.html', {
                "name": name,
                "cell": cell,
                "address": address,
                "email": email,
            })
      
        Customer.objects.create(
            name=name,
            cell=cell,
            address=address,
            email=email,
            date_joined=timezone.now(),
            remarks="manual_entry"
        )
        messages.success(request, "Customer added successfully!")
        return redirect('customers')

    return render(request, 'add_customer.html')

@allow_customers
def edit_customer(request, id):
    customer = get_object_or_404(Customer, id=id)

    if request.method == "POST":
        name = request.POST.get("name")
        cell = request.POST.get("cell")
        address = request.POST.get("address")
        email = request.POST.get("email")

        # Check if another customer already has this phone number
        if Customer.objects.filter(cell=cell).exclude(id=customer.id).exists():
            # Return with error message
            return render(
                request,
                "edit_customer.html",
                {
                    "customer": customer,
                    "error": f"Phone number {cell} is already registered with another customer."
                },
            )

        # Save only if phone number is unique
        customer.name = name
        customer.cell = cell
        customer.address = address
        customer.email = email
        customer.save()

        return redirect("customers")

    return render(request, "edit_customer.html", {"customer": customer})

from django.shortcuts import render
from django.db.models import Prefetch
from .models import Purchase, PurchaseItem, Supplier

def purchase_items_view(request):

    purchases = Purchase.objects.select_related(
        "supplier"
    ).prefetch_related(
        Prefetch(
            "items",
            queryset=PurchaseItem.objects.select_related("item")
        )
    ).order_by("-created_at", "-id")

    supplier_id = request.GET.get("supplier")
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    if supplier_id:
        purchases = purchases.filter(supplier_id=supplier_id)
    if start_date:
        purchases = purchases.filter(created_at__date__gte=start_date)
    if end_date:
        purchases = purchases.filter(created_at__date__lte=end_date)

    return render(request, "purchase_items.html", {
        "purchases": purchases,
        "suppliers": Supplier.objects.all(),
        "selected_supplier": supplier_id,
        "start_date": start_date,
        "end_date": end_date,
    })
from django.http import JsonResponse
from .models import PurchaseItem

def purchase_products_api(request):
    invoice = request.GET.get("invoice")

    items = PurchaseItem.objects.filter(
        purchase__invoice_no=invoice
    ).values(
        "item_name",
        "quantity",
        "unit",
        "unit_price",
        "total_price",
        "batch_no",
        "expiry_date",
    )

    return JsonResponse({
        "items": list(items)
    })




# views.py
import base64
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_GET
from .models import PurchasePayment  # adjust import path if needed

# decorator you mentioned earlier
# from .decorators import allow_purchase  # if you have one; otherwise remove the decorator
# use allow_purchase if required
try:
    from .decorators import allow_purchase
except Exception:
    def allow_purchase(fn):
        return fn


def _serialize_payments_for_invoice(invoice_no):
    """
    Helper: returns list of dicts for payments for purchase invoice_no.
    Adjust field names to match your models.
    """
    payments_qs = PurchasePayment.objects.filter(purchase__invoice_no=invoice_no).order_by('payment_date', 'id')
    data = []
    for p in payments_qs:
        purchase = getattr(p, 'purchase', None)
        supplier = getattr(purchase, 'supplier', None) if purchase else None

        # adapt fields if your model uses different names
        payment_date = getattr(p, 'payment_date', None)
        payment_date_str = payment_date.strftime("%Y-%m-%d") if getattr(payment_date, 'strftime', None) else (str(payment_date) if payment_date else "")

        data.append({
            "payment_amount": str(getattr(p, 'payment_amount', getattr(p, 'amount', None)) or ""),
            "payment_mode": getattr(p, 'payment_mode', getattr(p, 'mode', "")) or "",
            "payment_reference": getattr(p, 'payment_reference', getattr(p, 'reference', "")) or "",
            "purchase_id": getattr(purchase, 'id', None),
            "payment_date": payment_date_str,
            "supplier_id": getattr(supplier, 'id', None) or getattr(supplier, 'supplier_id', None),
            "balance_amount": str(getattr(p, 'balance_amount', None) or ""),
            "total_amount": str(getattr(purchase, 'total_amount', None) or ""),
        })
    return data


@require_GET
@allow_purchase
def purchase_payments_api(request, invoice_no):
    """
    A: Direct path view. URL: /api/purchase-payments/<invoice_no>/
    IMPORTANT: This will NOT match when invoice_no contains slashes (/).
    """
    if not invoice_no:
        return JsonResponse({"payments": []})

    payments_data = _serialize_payments_for_invoice(invoice_no)
    return JsonResponse({"payments": payments_data})


@require_GET
@allow_purchase
def purchase_payments_api_b64(request, invoice_b64):
    """
    B: Path view that accepts base64-encoded invoice.
    URL: /api/purchase-payments/b64/<invoice_b64>/
    The client must base64-encode the invoice (URL-safe).
    """
    if not invoice_b64:
        return JsonResponse({"payments": []})

    try:
        # invoice_b64 is normal base64 (not URLsafe); decode robustly
        # handle both urlsafe and normal base64
        try:
            decoded_bytes = base64.urlsafe_b64decode(invoice_b64 + "===")
        except Exception:
            decoded_bytes = base64.b64decode(invoice_b64 + "===")
        invoice_no = decoded_bytes.decode('utf-8')
    except Exception as exc:
        return HttpResponseBadRequest(f"Invalid base64 invoice: {exc}")

    payments_data = _serialize_payments_for_invoice(invoice_no)
    return JsonResponse({"payments": payments_data})


@require_GET
@allow_purchase
def purchase_payments_api_query(request):
    """
    C: Query param view. URL: /api/purchase-payments/?invoice=...
    This is the simplest and safest approach when invoice contains special characters.
    """
    invoice_no = request.GET.get("invoice")
    if not invoice_no:
        return JsonResponse({"payments": []})

    payments_data = _serialize_payments_for_invoice(invoice_no)
    return JsonResponse({"payments": payments_data})

@allow_expenses
def create_expense(request):
    if request.method == 'POST':
        form = ExpenseForm(request.POST, request.FILES)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.category_detail = request.POST.get('category_detail')  
            expense.save()
            return redirect('expense')
    else:
        form = ExpenseForm()
    return render(request, 'expense.html', {'form': form})

@allow_expenses
def edit_expense(request, expense_id):
    expense = get_object_or_404(Expense, pk=expense_id)
    if request.method == 'POST':
        form = ExpenseForm(request.POST, request.FILES, instance=expense)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.category_detail = request.POST.get('category_detail')
            expense.save()
            messages.success(request, "Expense updated successfully.")
            return redirect('expense_list')
    else:
        form = ExpenseForm(instance=expense)
        if 'datetime' in form.fields:
            form.fields['datetime'].widget.attrs.pop('readonly', None)

    return render(request, 'expense.html', {
        'form': form,
        'is_edit': True,
        'expense': expense,
    })

@allow_expenses
def delete_expense(request, expense_id):
    expense = get_object_or_404(Expense, pk=expense_id)
    if request.method == 'POST':
        if expense.attachment:
            expense.attachment.delete(save=False)
        expense.delete()
        messages.success(request, "Expense deleted successfully.")
    return redirect('expense_list')

from django.shortcuts import render
from django.utils.timezone import localtime
from collections import defaultdict
from django.db.models import Sum

from .models import Expense
from .decorators import allow_expenses


@allow_expenses
def expense_list(request):
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    category = request.GET.get('category', 'all')

    expenses = Expense.objects.all()

    # ---------------------------
    # Date Filters
    # ---------------------------
    if from_date:
        expenses = expenses.filter(datetime__date__gte=from_date)

    if to_date:
        expenses = expenses.filter(datetime__date__lte=to_date)

    # ---------------------------
    # Category Filter
    # ---------------------------
    if category and category != 'all':
        expenses = expenses.filter(category=category)

    expenses = expenses.order_by('-datetime')

    # ---------------------------
    # Group by Date
    # ---------------------------
    expenses_by_date = defaultdict(list)
    for expense in expenses:
        local_dt = localtime(expense.datetime)
        date_key = local_dt.date()
        expenses_by_date[date_key].append(expense)

    # ---------------------------
    # Category Totals
    # ---------------------------
    category_totals = (
        expenses
        .values('category')
        .annotate(total=Sum('amount'))
        .order_by('category')
    )

    category_totals_dict = {
        dict(Expense.CATEGORY_CHOICES)[item['category']]: item['total']
        for item in category_totals
    }

    context = {
        'expenses_by_date': dict(expenses_by_date),
        'from_date': from_date,
        'to_date': to_date,
        'selected_category': category,
        'category_totals': category_totals_dict,
        'show_totals': bool(from_date or to_date or category != 'all'),
    }

    return render(request, 'expense_list.html', context)

def backup_company_details(instance, backup_dir):
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(backup_dir, f"company_details_{timestamp}.json")

    data = serialize('json', [instance])  
    with open(backup_file, 'w') as f:
        f.write(data)

    print(f"CompanyDetails backup saved at: {backup_file}")


###############################################
#  CLEAN & SAFE MIGRATION ENGINE (Option A2)
#  Only mapped columns are inserted into PG.
#  PG NOT NULL w/out default → STOP migration.
###############################################

import json
import uuid
import threading
from concurrent.futures import ThreadPoolExecutor

import pyodbc
import psycopg2
from psycopg2 import errors

from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse, HttpResponseBadRequest
from django.core.paginator import Paginator
from django.core.cache import cache
from django.conf import settings
from django.core.mail import send_mail

from .models import MigrationLog


# ---------------------------------------
# DB SETTINGS
# ---------------------------------------
MSSQL_CONN_STR = (
    "Driver={ODBC Driver 17 for SQL Server};"
    "Server=192.168.0.113,1433;"
    "Database=MahilMart-Analytics;"
    "Uid=mahilmartuser;"
    "Pwd=Admin@123;"
    "Trusted_Connection=no;"
    "TrustServerCertificate=yes;"
)

_pg_settings = settings.DATABASES.get("default", {})
POSTGRES_PARAMS = {
    "host": _pg_settings.get("HOST") or "localhost",
    "port": _pg_settings.get("PORT") or "5432",
    "user": _pg_settings.get("USER") or "",
    "password": _pg_settings.get("PASSWORD") or "",
    "dbname": _pg_settings.get("NAME") or "",
}

executor = ThreadPoolExecutor(max_workers=4)
job_lock = threading.Lock()
migration_jobs = {}


# =====================================================
# UTIL
# =====================================================
def clean_value(value):
    """Normalize MSSQL values for PostgreSQL."""
    if value in ["", None, " "]:
        return None
    if isinstance(value, str) and value.strip() == "":
        return None
    return value


def apply_mapping(row_dict, mapping):
    """Apply column mapping MSSQL -> PG."""
    result = {}
    for mssql_col, pg_col in mapping.items():
        result[pg_col] = clean_value(row_dict.get(mssql_col))
    return result


def get_pg_required_columns(pg_cur, table_name):
    """
    Returns a list of NOT NULL PG columns that do NOT have default values
    and are NOT the auto 'id' column.

    These MUST be mapped, otherwise migration should stop.
    """
    pg_cur.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = %s
          AND table_schema = 'public'
          AND is_nullable = 'NO'
          AND column_default IS NULL
        """,
        [table_name],
    )
    required = []
    for (col,) in pg_cur.fetchall():
        # 👉 DO NOT require the 'id' column (identity/autoincrement)
        if col.lower() == "id":
            continue
        required.append(col)
    return required


# =====================================================
# MAIN MIGRATION FUNCTION (Option A2, fixed for id)
# =====================================================
def run_table_migration(mssql_table, postgres_table=None):
    """
    Generic MSSQL → PostgreSQL table copy.

    - Only mapped columns are inserted.
    - Validates PG required fields BEFORE inserting.
    - If a required PG column is NOT mapped → STOP (Option A2).
    - 'id' is NOT required to be mapped (PG generates it).
    """

    # Handle Supplier special-case naming if no explicit pg table passed
    if not postgres_table:
        if mssql_table.lower() == "supplier":
            postgres_table = "MahilMartPOS_App_supplier"
        else:
            postgres_table = mssql_table

    print(f"\n🚀 MIGRATE: MSSQL '{mssql_table}' → PG '{postgres_table}'")

    # Load saved mapping from MigrationLog
    mapping_logs = (
        MigrationLog.objects.filter(
            mssql_table=mssql_table,
            postgres_table=postgres_table,
        )
        .exclude(column_mapping=None)
        .order_by("-id")
    )
    saved_mapping = mapping_logs[0].column_mapping if mapping_logs else {}
    if saved_mapping:
        print("ℹ️ Using saved mapping:", saved_mapping)

    # Connect DBs
    mssql_conn = pyodbc.connect(MSSQL_CONN_STR)
    mssql_cur = mssql_conn.cursor()
    pg_conn = psycopg2.connect(**POSTGRES_PARAMS)
    pg_cur = pg_conn.cursor()

    try:
        # ------------------------------------------
        # Load MSSQL columns
        # ------------------------------------------
        mssql_cur.execute(
            f"""
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = '{mssql_table}'
            ORDER BY ORDINAL_POSITION
        """
        )
        all_cols = [c[0] for c in mssql_cur.fetchall()]

        # Skip MSSQL "id" column if present
        mssql_cols = [c for c in all_cols if c.lower() != "id"]

        if not mssql_cols:
            raise Exception("No valid MSSQL columns found")

        select_cols = ",".join(f"[{c}]" for c in mssql_cols)
        mssql_cur.execute(f"SELECT {select_cols} FROM [{mssql_table}]")
        raw_rows = mssql_cur.fetchall()

        rows = []
        for r in raw_rows:
            d = {}
            for idx, col in enumerate(mssql_cols):
                d[col] = r[idx]
            rows.append(d)

        print(f"📦 Loaded {len(rows)} rows from MSSQL table '{mssql_table}'")

        # ------------------------------------------
        # Determine mapping
        # ------------------------------------------
        if saved_mapping:
            mapping = saved_mapping
        else:
            # Auto-map by column name
            pg_cur.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema='public' AND table_name=%s
                ORDER BY ordinal_position
            """,
                [postgres_table],
            )
            pg_cols = [c[0] for c in pg_cur.fetchall()]
            print(f"PG columns for '{postgres_table}':", pg_cols)

            mapping = {}
            lower_pg = {c.lower(): c for c in pg_cols}
            for m in mssql_cols:
                if m.lower() in lower_pg:
                    mapping[m] = lower_pg[m.lower()]

        if not mapping:
            raise Exception(
                f"No column mapping available (MSSQL: {mssql_table}, PG: {postgres_table}). "
                f"Please create mapping in the UI first."
            )

        pg_columns = list(mapping.values())
        print("✅ Final column mapping:", mapping)

        # ------------------------------------------
        # VALIDATION (Option A2)
        # Stop migration if PG has required fields NOT mapped
        # ------------------------------------------
        required_pg_cols = get_pg_required_columns(pg_cur, postgres_table)
        missing_required = [c for c in required_pg_cols if c not in pg_columns]

        if missing_required:
            raise Exception(
                f"Unable to migrate: Missing required PG columns {missing_required}. "
                f"Map these columns or add defaults before migrating."
            )

        # ------------------------------------------
        # Apply mapping to rows
        # ------------------------------------------
        mapped_rows = [apply_mapping(r, mapping) for r in rows]

        if not mapped_rows:
            print("⚠️ No rows to insert after mapping.")
            return 0

        # ------------------------------------------
        # Insert data
        # ------------------------------------------
        col_str = ",".join(f'"{c}"' for c in pg_columns)
        placeholders = ",".join(["%s"] * len(pg_columns))

        inserted = 0

        for row_dict in mapped_rows:
            values = [clean_value(row_dict.get(c)) for c in pg_columns]

            try:
                pg_cur.execute(
                    f'INSERT INTO "{postgres_table}" ({col_str}) VALUES ({placeholders})',
                    values,
                )
                inserted += 1

            except errors.NotNullViolation as e:
                # A NOT NULL column without value slipped through
                print("❌ NOT NULL violation, row skipped:", e)
                continue
            except Exception as e:
                # For now, stop on first unexpected error so you can see it clearly
                print("❌ INSERT ERROR:", e)
                raise Exception(f"Insert failed for table {postgres_table}: {e}")

        pg_conn.commit()
        print(f"✅ SUCCESS: inserted {inserted} rows into '{postgres_table}'")
        return inserted

    finally:
        try:
            mssql_conn.close()
        except Exception:
            pass
        try:
            pg_conn.close()
        except Exception:
            pass


# =====================================================
# VIEWS / AJAX
# =====================================================
def db_migration_tool(request):
    logs = MigrationLog.objects.all().order_by("-migrated_at")
    paginator = Paginator(logs, 20)
    page = paginator.get_page(request.GET.get("page"))
    return render(request, "db_migrate.html", {"logs": page})


def ajax_load_mssql_tables(request):
    try:
        conn = pyodbc.connect(MSSQL_CONN_STR)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sys.tables ORDER BY name")
        tables = [r[0] for r in cur.fetchall()]
        conn.close()
        return JsonResponse({"status": "ok", "tables": tables})
    except Exception:
        return JsonResponse({"status": "error", "tables": []})


def ajax_get_postgres_tables(request):
    try:
        pg = psycopg2.connect(**POSTGRES_PARAMS)
        cur = pg.cursor()
        cur.execute(
            """
            SELECT table_name FROM information_schema.tables
            WHERE table_schema='public' ORDER BY table_name
        """
        )
        tables = [r[0] for r in cur.fetchall()]
        pg.close()
        return JsonResponse({"status": "ok", "tables": tables})
    except Exception:
        return JsonResponse({"status": "error", "tables": []})


def ajax_get_columns(request, table_name):
    try:
        # MSSQL
        conn = pyodbc.connect(MSSQL_CONN_STR)
        cur = conn.cursor()
        cur.execute(
            f"""
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME='{table_name}'
            ORDER BY ORDINAL_POSITION
        """
        )
        mssql_cols = [r[0] for r in cur.fetchall()]
        conn.close()

        # PG
        pg_table = request.GET.get("pg", table_name)
        pg = psycopg2.connect(**POSTGRES_PARAMS)
        cur = pg.cursor()
        cur.execute(
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_schema='public' AND table_name=%s
            ORDER BY ordinal_position
        """,
            [pg_table],
        )
        pg_cols = [r[0] for r in cur.fetchall()]
        pg.close()

        return JsonResponse(
            {
                "status": "ok",
                "mssql_columns": mssql_cols,
                "pg_columns": pg_cols,
                "auto_pg_table": pg_table,
            }
        )

    except Exception as e:
        return JsonResponse({"status": "error", "error": str(e)})


def ajax_save_mapping(request):
    try:
        data = json.loads(request.body.decode())
        MigrationLog.objects.create(
            mssql_table=data["mssql_table"],
            postgres_table=data["pg_table"],
            column_mapping=data["mapping"],
            status="MappingSaved",
        )
        return JsonResponse({"status": "ok"})
    except Exception as e:
        return JsonResponse({"status": "error", "error": str(e)})


def migrate_single_table(request):
    if request.method != "POST":
        return redirect("db_migration_tool")

    mssql_table = request.POST.get("mssql_table")
    pg_table = request.POST.get("postgres_table") or None

    # Determine final PG table for logging (same rule as run_table_migration)
    if pg_table:
        log_pg = pg_table
    else:
        log_pg = (
            "MahilMartPOS_App_supplier"
            if mssql_table.lower() == "supplier"
            else mssql_table
        )

    log = MigrationLog(mssql_table=mssql_table, postgres_table=log_pg)

    try:
        count = run_table_migration(mssql_table, pg_table)
        log.status = "Success"
        log.migrated_rows = count
        messages.success(request, f"Imported {count} rows into {log_pg}")

    except Exception as e:
        log.status = "Failed"
        log.error_message = str(e)
        messages.error(request, f"Migration failed: {e}")

    log.save()
    return redirect("db_migration_tool")


# =====================================================
# JOB SYSTEM (ALL TABLES)
# =====================================================
def start_migration_job(request):
    if (
        request.method != "POST"
        or request.headers.get("X-Requested-With") != "XMLHttpRequest"
    ):
        return HttpResponseBadRequest("Invalid request")

    payload = json.loads(request.body.decode("utf-8"))
    mode = payload.get("mode", "all")

    if mode == "all":
        try:
            conn = pyodbc.connect(MSSQL_CONN_STR)
            cur = conn.cursor()
            cur.execute("SELECT name FROM sys.tables ORDER BY name")
            tables = [r[0] for r in cur.fetchall()]
            conn.close()
        except Exception:
            return JsonResponse(
                {"status": "error", "error": "MSSQL connection failed"}
            )
    else:
        return JsonResponse({"status": "error", "error": "Unsupported mode"})

    job_id = str(uuid.uuid4())
    job_data = {
        "status": "running",
        "total_tables": len(tables),
        "completed_tables": 0,
        "tables": {},
    }

    for t in tables:
        job_data["tables"][t] = {"status": "pending", "rows": 0, "error": None}

    with job_lock:
        migration_jobs[job_id] = job_data

    def worker(table_name):
        with job_lock:
            migration_jobs[job_id]["tables"][table_name]["status"] = "running"

        pg_name = (
            "MahilMartPOS_App_supplier"
            if table_name.lower() == "supplier"
            else table_name
        )
        log = MigrationLog(mssql_table=table_name, postgres_table=pg_name)

        try:
            count = run_table_migration(table_name, None)
            log.migrated_rows = count
            log.status = "Success"

            with job_lock:
                job = migration_jobs[job_id]
                job["tables"][table_name]["status"] = "success"
                job["tables"][table_name]["rows"] = count
                job["completed_tables"] += 1

        except Exception as e:
            log.status = "Failed"
            log.error_message = str(e)

            with job_lock:
                job = migration_jobs[job_id]
                job["tables"][table_name]["status"] = "failed"
                job["tables"][table_name]["error"] = str(e)
                job["completed_tables"] += 1

        finally:
            log.save()

            with job_lock:
                job = migration_jobs[job_id]
                if job["completed_tables"] >= job["total_tables"]:
                    job["status"] = "finished"

    for t in tables:
        executor.submit(worker, t)

    return JsonResponse({"status": "ok", "job_id": job_id})


def migration_job_status(request, job_id):
    with job_lock:
        job = migration_jobs.get(job_id)

    if not job:
        return JsonResponse({"status": "unknown"})

    total = job["total_tables"]
    done = job["completed_tables"]

    return JsonResponse(
        {
            "status": job["status"],
            "total_tables": total,
            "completed_tables": done,
            "percent": int(done / total * 100) if total else 100,
            "tables": job["tables"],
        }
    )


def migrate_all_tables(request):
    try:
        conn = pyodbc.connect(MSSQL_CONN_STR)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sys.tables ORDER BY name")
        tables = [r[0] for r in cur.fetchall()]
        conn.close()

        for t in tables:
            pg_table = (
                "MahilMartPOS_App_supplier" if t.lower() == "supplier" else t
            )
            log = MigrationLog(mssql_table=t, postgres_table=pg_table)

            try:
                count = run_table_migration(t, None)
                log.status = "Success"
                log.migrated_rows = count
            except Exception as e:
                log.status = "Failed"
                log.error_message = str(e)

            log.save()

        messages.success(request, "Full migration completed successfully!")
        cache.delete("mssql_tables")

    except Exception as e:
        messages.error(request, f"Failed: {e}")

    return redirect("db_migration_tool")


from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from datetime import timedelta
from django.utils import timezone

from .models import ActivityLog


@login_required
def activity_log_view(request):
    # Base queryset (only login/logout)
    qs = ActivityLog.objects.filter(
        action__in=["LOGIN", "LOGOUT"]
    ).order_by("created_at")

    # --------------------
    # Filters
    # --------------------
    user = request.GET.get("user")
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    if user:
        qs = qs.filter(username__icontains=user)

    if start_date:
        qs = qs.filter(created_at__date__gte=start_date)

    if end_date:
        qs = qs.filter(created_at__date__lte=end_date)

    # --------------------
    # Pair LOGIN + LOGOUT
    # --------------------
    sessions = []
    open_sessions = {}
    def resolve_role(log):
        if log.role:
            return log.role

        user_obj = log.user or User.objects.filter(username=log.username).first()
        if not user_obj:
            return "N/A"

        if user_obj.is_superuser:
            return "Admin"
        if user_obj.is_staff:
            return "Supervisor"

        group_names = list(user_obj.groups.values_list("name", flat=True))
        if group_names:
            return ", ".join(group_names)

        return "Cashier"

    def append_session_entry(login_log, logout_at=None):
        logout_time_str = None
        duration_str = None
        if logout_at is not None:
            safe_logout_at = max(logout_at, login_log.created_at)
            logout_time_str = safe_logout_at.strftime("%d-%m-%Y %H:%M:%S")
            duration_str = _format_duration(safe_logout_at - login_log.created_at)

        sessions.append({
            "username": login_log.username,
            "role": resolve_role(login_log),
            "login_time": login_log.created_at.strftime("%d-%m-%Y %H:%M:%S"),
            "logout_time": logout_time_str,
            "duration": duration_str,
            "ip_address": login_log.ip_address,
        })

    for log in qs:
        key = (log.username, log.ip_address)

        if log.action == "LOGIN":
            if key in open_sessions:
                stale_login = open_sessions.pop(key)
                append_session_entry(stale_login, log.created_at)
            open_sessions[key] = log

        elif log.action == "LOGOUT" and key in open_sessions:
            login_log = open_sessions.pop(key)
            append_session_entry(login_log, log.created_at)

    # --------------------
    # Still logged-in users
    # --------------------
    for login_log in open_sessions.values():
        append_session_entry(login_log, None)

    # Latest sessions first
    sessions.reverse()

    total_sessions = len(sessions)
    active_sessions = sum(1 for entry in sessions if not entry["logout_time"])
    closed_sessions = total_sessions - active_sessions
    unique_users = len({entry["username"] for entry in sessions if entry.get("username")})

    # --------------------
    # Pagination
    # --------------------
    paginator = Paginator(sessions, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    users = User.objects.values_list("username", flat=True).order_by("username")
    query_params = request.GET.copy()
    query_params.pop("page", None)
    context = {
        "sessions": page_obj,
        "user_list": users,
        "total_sessions": total_sessions,
        "active_sessions": active_sessions,
        "closed_sessions": closed_sessions,
        "unique_users": unique_users,
        "query_string": query_params.urlencode(),
    }

    return render(request, "activity_log.html", context)


def _format_duration(duration: timedelta) -> str:
    total_seconds = int(duration.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60

    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"

from django.shortcuts import render, redirect
from django.contrib import messages
from MahilMartPOS_App.models import EmailConfig, EmailLog
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.db.utils import OperationalError, ProgrammingError


@login_required
def email_settings_view(request):
    config = EmailConfig.objects.filter(is_active=True).first()

    if request.method == "POST":
        if request.POST.get("toggle_only") == "1":
            if not config:
                return JsonResponse({
                    "success": False,
                    "message": "Save SMTP settings first."
                }, status=400)

            config.access_denied_alert_enabled = request.POST.get("access_denied_alert_enabled") == "on"
            config.low_stock_alert_enabled = request.POST.get("low_stock_alert_enabled") == "on"
            config.no_stock_alert_enabled = request.POST.get("no_stock_alert_enabled") == "on"
            config.alert_enabled = config.low_stock_alert_enabled or config.no_stock_alert_enabled
            config.use_tls = request.POST.get("use_tls") == "on"
            config.save()

            apply_email_settings()

            return JsonResponse({
                "success": True,
                "message": "Alert settings updated."
            })

        email_host = (request.POST.get("email_host") or "").strip()
        email_port_raw = (request.POST.get("email_port") or "").strip()
        use_tls = request.POST.get("use_tls") == "on"
        email_user = (request.POST.get("email_host_user") or "").strip()
        email_pass = (request.POST.get("email_host_password") or "").strip()
        default_from = (request.POST.get("default_from_email") or "").strip()
        alert_recipients = (request.POST.get("alert_recipients") or "").strip()
        access_denied_alert_enabled = request.POST.get("access_denied_alert_enabled") == "on"
        low_stock_alert_enabled = request.POST.get("low_stock_alert_enabled") == "on"
        no_stock_alert_enabled = request.POST.get("no_stock_alert_enabled") == "on"
        alert_enabled = low_stock_alert_enabled or no_stock_alert_enabled

        if not email_port_raw.isdigit():
            messages.error(request, "Email port must be a valid number.")
            return redirect("email_settings")
        email_port = int(email_port_raw)

        if config:
            config.email_host = email_host
            config.email_port = email_port
            config.use_tls = use_tls
            config.email_host_user = email_user
            if email_pass:
                config.email_host_password = email_pass
            config.default_from_email = default_from
            config.alert_recipients = alert_recipients
            config.alert_enabled = alert_enabled
            config.access_denied_alert_enabled = access_denied_alert_enabled
            config.low_stock_alert_enabled = low_stock_alert_enabled
            config.no_stock_alert_enabled = no_stock_alert_enabled
            config.is_active = True
            config.save()
            EmailConfig.objects.exclude(pk=config.pk).update(is_active=False)
        else:
            if not email_pass:
                messages.error(request, "Email password is required for new configuration.")
                return redirect("email_settings")
            EmailConfig.objects.all().update(is_active=False)
            EmailConfig.objects.create(
                email_host=email_host,
                email_port=email_port,
                use_tls=use_tls,
                email_host_user=email_user,
                email_host_password=email_pass,
                default_from_email=default_from,
                alert_recipients=alert_recipients,
                alert_enabled=alert_enabled,
                access_denied_alert_enabled=access_denied_alert_enabled,
                low_stock_alert_enabled=low_stock_alert_enabled,
                no_stock_alert_enabled=no_stock_alert_enabled,
                is_active=True
            )

        apply_email_settings()
        messages.success(request, "Email settings saved successfully.")
        return redirect("email_settings")

    current_from_email = None
    current_recipients = []
    access_denied_enabled = True
    low_stock_enabled = True
    no_stock_enabled = True

    if config:
        access_denied_enabled = config.access_denied_alert_enabled
        low_stock_enabled = config.low_stock_alert_enabled
        no_stock_enabled = config.no_stock_alert_enabled
        current_from_email = config.default_from_email or config.email_host_user
        if config.alert_recipients:
            current_recipients = [e.strip() for e in config.alert_recipients.split(",") if e.strip()]
        elif current_from_email:
            current_recipients = [current_from_email]

    if not current_from_email:
        current_from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or getattr(settings, "EMAIL_HOST_USER", None)

    if not current_recipients:
        current_recipients = [email for _, email in settings.ADMINS] if getattr(settings, "ADMINS", None) else []

    return render(request, "email_settings.html", {
        "config": config,
        "current_from_email": current_from_email or "Not set",
        "current_recipients": ", ".join(current_recipients) if current_recipients else "Not set",
        "access_denied_enabled": access_denied_enabled,
        "low_stock_enabled": low_stock_enabled,
        "no_stock_enabled": no_stock_enabled,
    })


def _safe_log_email(**kwargs):
    try:
        EmailLog.objects.create(**kwargs)
    except Exception as exc:
        print("Email log failed:", exc)


def _send_stock_alert(request, low_stock_items, no_stock_items, low_stock_count, no_stock_count):
    config = EmailConfig.objects.filter(is_active=True).first()
    low_enabled = True
    no_enabled = True

    if config:
        low_enabled = config.low_stock_alert_enabled
        no_enabled = config.no_stock_alert_enabled

    effective_low_count = low_stock_count if low_enabled else 0
    effective_no_count = no_stock_count if no_enabled else 0

    if effective_low_count <= 0 and effective_no_count <= 0:
        return

    today = now().date()
    latest_sent = EmailLog.objects.filter(
        event_type="system",
        subject__startswith="Stock Alert",
        status="sent",
        created_at__date=today
    ).order_by("-created_at").first()

    if latest_sent:
        match = re.search(r"Stock Alert:\s*(\d+)\s*Out of Stock,\s*(\d+)\s*Low Stock", latest_sent.subject)
        if match:
            last_out = int(match.group(1))
            last_low = int(match.group(2))
            if last_out == effective_no_count and last_low == effective_low_count:
                return

    # Prepare item snapshots (limit to avoid huge emails)
    low_items = list(low_stock_items[:50]) if low_enabled else []
    no_items = list(no_stock_items[:50]) if no_enabled else []

    subject = f"Stock Alert: {effective_no_count} Out of Stock, {effective_low_count} Low Stock"

    def build_rows(items, is_low=False):
        rows = ""
        for item in items:
            code = item.get("code", "-")
            name = item.get("item_name", "-")
            unit = item.get("unit", "-")
            qty = item.get("total_qty", 0)
            min_stock = item.get("min_stock_val", "-")
            rows += f"""
                <tr>
                    <td style="padding:8px; border:1px solid #e2e8f0;">{code}</td>
                    <td style="padding:8px; border:1px solid #e2e8f0;">{name}</td>
                    <td style="padding:8px; border:1px solid #e2e8f0;">{unit}</td>
                    <td style="padding:8px; border:1px solid #e2e8f0; text-align:right;">{qty}</td>
                    <td style="padding:8px; border:1px solid #e2e8f0; text-align:right;">{min_stock}</td>
                </tr>
            """
        if not rows:
            rows = f"""
                <tr>
                    <td colspan="5" style="padding:10px; border:1px solid #e2e8f0; text-align:center; color:#64748b;">
                        {"No low stock items." if is_low else "No out of stock items."}
                    </td>
                </tr>
            """
        return rows

    html_message = f"""
    <div style="font-family:Segoe UI, sans-serif; background:#f8fafc; padding:24px;">
        <div style="max-width:760px; margin:0 auto; background:#ffffff; border-radius:12px; border:1px solid #e2e8f0; overflow:hidden;">
            <div style="background:linear-gradient(135deg,#0f172a,#1e293b); color:#fff; padding:16px 20px;">
                <h2 style="margin:0; font-size:18px;">Stock Alert</h2>
                <p style="margin:6px 0 0; font-size:13px; opacity:0.9;">{now().strftime('%d %b %Y %H:%M')}</p>
            </div>
            <div style="padding:20px;">
                <p style="margin:0 0 16px; color:#334155;">
                    There are <strong>{effective_no_count}</strong> out of stock items and
                    <strong>{effective_low_count}</strong> low stock items.
                </p>

                <h3 style="margin:16px 0 8px; font-size:15px; color:#b91c1c;">Out of Stock</h3>
                <table style="width:100%; border-collapse:collapse; font-size:13px;">
                    <thead>
                        <tr style="background:#fef2f2; color:#991b1b;">
                            <th style="padding:8px; border:1px solid #e2e8f0; text-align:left;">Code</th>
                            <th style="padding:8px; border:1px solid #e2e8f0; text-align:left;">Item</th>
                            <th style="padding:8px; border:1px solid #e2e8f0; text-align:left;">Unit</th>
                            <th style="padding:8px; border:1px solid #e2e8f0; text-align:right;">Qty</th>
                            <th style="padding:8px; border:1px solid #e2e8f0; text-align:right;">Min Stock</th>
                        </tr>
                    </thead>
                    <tbody>
                        {build_rows(no_items)}
                    </tbody>
                </table>

                <h3 style="margin:20px 0 8px; font-size:15px; color:#b45309;">Low Stock</h3>
                <table style="width:100%; border-collapse:collapse; font-size:13px;">
                    <thead>
                        <tr style="background:#fffbeb; color:#92400e;">
                            <th style="padding:8px; border:1px solid #e2e8f0; text-align:left;">Code</th>
                            <th style="padding:8px; border:1px solid #e2e8f0; text-align:left;">Item</th>
                            <th style="padding:8px; border:1px solid #e2e8f0; text-align:left;">Unit</th>
                            <th style="padding:8px; border:1px solid #e2e8f0; text-align:right;">Qty</th>
                            <th style="padding:8px; border:1px solid #e2e8f0; text-align:right;">Min Stock</th>
                        </tr>
                    </thead>
                    <tbody>
                        {build_rows(low_items, is_low=True)}
                    </tbody>
                </table>

                <p style="margin:18px 0 0; font-size:12px; color:#94a3b8;">
                    This alert is generated automatically by MahilMart POS.
                </p>
            </div>
        </div>
    </div>
    """

    email_sent = False
    email_error = None
    recipients = []

    try:
        apply_email_settings()

        if config and config.alert_recipients:
            recipients = [e.strip() for e in config.alert_recipients.split(",") if e.strip()]

        if not recipients and config:
            fallback = config.default_from_email or config.email_host_user
            if fallback:
                recipients = [fallback]

        if not recipients:
            recipients = [email for _, email in settings.ADMINS] if getattr(settings, "ADMINS", None) else []

        from_email = None
        if config:
            from_email = config.default_from_email or config.email_host_user
        if not from_email:
            from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or getattr(settings, "EMAIL_HOST_USER", None)

        if recipients and from_email:
            email = EmailMultiAlternatives(
                subject=subject,
                body="",
                from_email=from_email,
                to=recipients,
            )
            email.attach_alternative(html_message, "text/html")
            email.send(fail_silently=False)
            email_sent = True
        else:
            email_error = "Email settings or recipients are not configured."

    except Exception as exc:
        email_error = str(exc)

    _safe_log_email(
        event_type="system",
        subject=subject,
        recipients=", ".join(recipients),
        status="sent" if email_sent else "failed",
        error_message=email_error,
        triggered_by=request.user if request and request.user.is_authenticated else None,
        request_path=request.path if request else None,
        ip_address=request.META.get("REMOTE_ADDR") if request else None,
    )


@login_required
def email_view_page(request):
    config = EmailConfig.objects.filter(is_active=True).first()
    return render(request, "email_view.html", {
        "config": config
    })


@login_required
def email_logs_view(request):
    try:
        logs = EmailLog.objects.all().order_by("-created_at")[:200]
        log_error = None
    except (OperationalError, ProgrammingError) as exc:
        logs = []
        log_error = f"Email log table is not ready. Run migrations. ({exc})"

    return render(request, "email_logs.html", {
        "logs": logs,
        "log_error": log_error
    })


@login_required
def email_preview_view(request):
    config = EmailConfig.objects.filter(is_active=True).first()
    recipients = []
    if config and config.alert_recipients:
        recipients = [e.strip() for e in config.alert_recipients.split(",") if e.strip()]
    if not recipients and config:
        fallback = config.default_from_email or config.email_host_user
        if fallback:
            recipients = [fallback]
    if not recipients:
        recipients = [email for _, email in settings.ADMINS] if getattr(settings, "ADMINS", None) else []

    from_email = None
    if config:
        from_email = config.default_from_email or config.email_host_user
    if not from_email:
        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or getattr(settings, "EMAIL_HOST_USER", None)

    return render(request, "email_preview.html", {
        "config": config,
        "from_email": from_email,
        "recipients_display": ", ".join(recipients) if recipients else "Not configured"
    })


@require_POST
@login_required
def email_test_view(request):
    test_email = (request.POST.get("email") or "").strip()
    if not test_email:
        return JsonResponse({"success": False, "message": "Email address is required."}, status=400)

    try:
        validate_email(test_email)
    except ValidationError:
        return JsonResponse({"success": False, "message": "Please enter a valid email address."}, status=400)

    config = EmailConfig.objects.filter(is_active=True).first()
    if not config:
        return JsonResponse({"success": False, "message": "Email settings are not configured."}, status=400)

    apply_email_settings()

    from_email = (
        config.default_from_email
        or config.email_host_user
        or getattr(settings, "DEFAULT_FROM_EMAIL", None)
        or getattr(settings, "EMAIL_HOST_USER", None)
    )
    if not from_email:
        return JsonResponse({"success": False, "message": "Default From Email is missing."}, status=400)

    subject = "MahilMart POS - Test Email"
    html_message = f"""
    <div style="font-family: Arial, sans-serif; padding: 16px;">
        <h2 style="color:#2563eb;">Email Test Successful</h2>
        <p>This is a test email from <strong>MahilMart POS</strong>.</p>
        <p>Recipient: {test_email}</p>
    </div>
    """

    try:
        email = EmailMultiAlternatives(
            subject=subject,
            body="Test email from MahilMart POS.",
            from_email=from_email,
            to=[test_email],
        )
        email.attach_alternative(html_message, "text/html")
        email.send(fail_silently=False)
        _safe_log_email(
            event_type="test",
            subject=subject,
            recipients=test_email,
            status="sent",
            triggered_by=request.user,
            request_path=request.path,
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return JsonResponse({"success": True, "message": f"Test email sent to {test_email}."})
    except Exception as e:
        _safe_log_email(
            event_type="test",
            subject=subject,
            recipients=test_email,
            status="failed",
            error_message=str(e),
            triggered_by=request.user,
            request_path=request.path,
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return JsonResponse({"success": False, "message": f"Failed to send test email. {e}"}, status=500)
