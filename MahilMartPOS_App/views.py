import json
import os,datetime
from django.db import models
from decimal import Decimal
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.db.models import Min, Q, Sum
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.csrf import csrf_exempt
from .forms import SupplierForm, CompanySettingsForm
from MahilMartPOS_App.models import Product as AppProduct
from django.db.models.functions import Trim
from datetime import datetime
from django.core.serializers import serialize
from django.contrib.auth.hashers import make_password, check_password
from django.core.paginator import Paginator
from .forms import OrderForm,OrderItem,ExpenseForm,PaymentForm
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
from django.db.models.functions import Abs
from django.utils.timezone import now, timedelta
from .models import Billing
from django.db.models import Sum, F, Case, When
from django.db.models import DecimalField, F, Sum
from django.db.models import F, ExpressionWrapper, DecimalField, CharField, Value, Case, When
from django.shortcuts import render
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from datetime import datetime, time
from django.utils.dateparse import parse_date
from django.contrib.auth.decorators import user_passes_test
from .decorators import access_required
from django.urls import reverse
from django.db import transaction
from .models import (
    Supplier,
    Customer,
    Billing,
    BillingItem,
    User,
    Item,
    ItemBarcode,
    Unit,
    Group,
    Brand,
    Purchase,
    PurchaseItem,
    Tax,
    CompanyDetails,
    Product,
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
)

def home(request):
    return render(request, 'home.html')

def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('dashboard')  # Redirect to dashboard
        else:
            return render(request, 'home.html', {'error': 'Invalid credentials'})
    
    return render(request, 'home.html')


def custom_permission_denied_view(request, exception=None):
    from django.contrib import messages
    from django.shortcuts import redirect

    messages.error(request, "🚫 You do not have permission to access this page.")
    return redirect('dashboard')  # make sure 'dashboard' exists in urls.py

@access_required(allowed_roles=['superuser'])
def company_settings_view(request):
    if request.method == 'POST':
        form = CompanySettingsForm(request.POST)
        if form.is_valid():
            instance = form.save()

            if instance.auto_backup:
                if instance.daily_backup_path:
                    backup_company_details(instance, instance.daily_backup_path)
                if instance.daily_backup_path:
                    backup_company_details(instance, instance.daily_backup_path)

            messages.success(request, "Company details saved and backup created.")
            return redirect('company_details')
        else:
            messages.error(request, "There was an error in the form.")
    else:
        form = CompanySettingsForm()

    return render(request, 'company_details.html', {'form': form})

@access_required(allowed_roles=['superuser'])
def view_company_details(request):
    company = CompanyDetails.objects.last()
    return render(request, 'view_company_details.html', {'company': company})

def dashboard_view(request):
    today = now().date()
    transaction_count = Billing.objects.filter(created_at__date=today).count()
    yesterday = today - timedelta(days=1)

    # Today's total sales (received + abs(balance))
    today_sales = Billing.objects.filter(date__date=today).annotate(
        total=F('received') + Abs(F('balance'))
    ).aggregate(sum_total=Sum('total'))['sum_total'] or 0

    # Yesterday's total sales
    yesterday_sales = Billing.objects.filter(date__date=yesterday).annotate(
        total=F('received') + Abs(F('balance'))
    ).aggregate(sum_total=Sum('total'))['sum_total'] or 0

    # Change percentage
    if yesterday_sales > 0:
        change_percentage = ((today_sales - yesterday_sales) / yesterday_sales) * 100
    else:
        change_percentage = 0

    # Aggregate stock quantities by code & name
    stock_qty_expr = Case(
        When(unit__icontains='bulk', then=F('split_unit')),
        default=F('quantity'),
        output_field=DecimalField(max_digits=20, decimal_places=10)
    )

    stock_aggregates = Inventory.objects.values('code', 'item_name', 'unit').annotate(total_qty=Sum(stock_qty_expr))

    no_stock_items = stock_aggregates.filter(total_qty__lte=0)
    no_stock_count = no_stock_items.count()

    low_stock_items = stock_aggregates.filter(total_qty__gt=0, total_qty__lt=10)
    low_stock_count = low_stock_items.count()

    # Date filter parameters
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    bills_qs = Billing.objects.select_related('customer')

    if start_date and end_date:
        start = parse_date(start_date)
        end = parse_date(end_date)
        
        if start and end:
            if start == end:
                bills_qs = bills_qs.filter(created_at__date=start)
            else:
                bills_qs = bills_qs.filter(created_at__date__gte=start, created_at__date__lte=end)

    recent_bills = (
        bills_qs
        .order_by('-created_at')
        .annotate(
            sale_amount=F('received') + Abs(F('balance')) + F('discount'),
            pending_amount=Abs(F('balance')),
            status=Case(
                When(balance__gt=0, then=Value('Pending')),
                When(balance__lt=0, then=Value('Pending')),
                default=Value('Completed'),
                output_field=CharField()
            ),
            customer_name=Case(
                When(customer__isnull=False, then=F('customer__name')),
                default=Value('Walk-in'),
                output_field=CharField()
            ),
            customer_phone=Case(
                When(customer__isnull=False, then=F('customer__cell')),
                default=Value('N/A'),
                output_field=CharField()
            )
        )
    )

    return render(request, 'dashboard.html', {
        'transaction_count': transaction_count,
        'today_sales': today_sales,
        'change_percentage': change_percentage,
        'no_stock_count': no_stock_count,
        'no_stock_items': no_stock_items,
        'low_stock_count': low_stock_count,
        'low_stock_items': low_stock_items,
        'recent_bills': recent_bills,
        'start_date': start_date,
        'end_date': end_date,
    })

def billing_detail_view(request, id):
    bill = get_object_or_404(Billing, id=id)
    return render(request, 'billing_detail.html', {'bill': bill})

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

def create_invoice_view(request):
    if request.method == 'GET' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        phone = request.GET.get('phone')
        customer = Customer.objects.filter(cell=phone).first()

        return JsonResponse({
            'name': customer.name if customer else '',
            'points': Billing.objects.filter(customer=customer).last().points if customer and Billing.objects.filter(customer=customer).exists() else 0,
            'email': customer.email if customer else '',
            'address': customer.address if customer else '',
            'date_joined': str(customer.date_joined.date()) if customer and customer.date_joined else '',
            'remarks': '',
        })

    if request.method == 'POST':
        try:
            cell = request.POST.get('cell').strip()
            name = request.POST.get('name').strip()
            email = request.POST.get('email', '').strip()
            address = request.POST.get('address', '').strip()

            # Get or create Customer
            customer, _ = Customer.objects.get_or_create(cell=cell, defaults={
                'name': name,
                'email': email,
                'address': address,
            })

            if not customer.name and name:
                customer.name = name
            if email and not customer.email:
                customer.email = email
            if address and not customer.address:
                customer.address = address
            customer.save()

            # Generate next bill number
            latest = Billing.objects.order_by('-id').first()
            base_bill_no = int(latest.bill_no) + 1 if latest and str(latest.bill_no).isdigit() else 1
            bill_no = str(base_bill_no)

            # Optional: for points accumulation
            previous_bill = Billing.objects.filter(customer=customer).order_by('-id').first()
            total_points = previous_bill.points if previous_bill else 0.0
            points_earned_total = 0.0

            # Create Billing object first
            billing = Billing.objects.create(
                customer=customer,
                to=request.POST.get('to'),
                bill_no=bill_no,
                date=timezone.now(),
                bill_type=request.POST.get('bill_type'),
                counter=request.POST.get('counter'),
                order_no=request.POST.get('order_no'),
                sale_type=request.POST.get('sale_type'),
                received=request.POST.get('received') or 0,
                balance=request.POST.get('balance') or 0,
                discount=request.POST.get('discount') or 0,
                points=total_points,
                points_earned=0,
                remarks=request.POST.get('remarks', ''),
                status_on="counter_bill"
            )

            # Process items
            snos = request.POST.getlist('sno')
            codes = request.POST.getlist('code')
            item_names = request.POST.getlist('item_name')
            units = request.POST.getlist('unit')
            qtys = request.POST.getlist('qty')
            mrsps = request.POST.getlist('mrsp')
            selling_prices = request.POST.getlist('sellingprice')

            for i in range(len(item_names)):
                if not any([codes[i].strip(), item_names[i].strip(), qtys[i].strip(), selling_prices[i].strip()]):
                    continue

                qty = round(float(qtys[i]), 2)
                mrp = round(float(mrsps[i]), 2)
                selling_price = round(float(selling_prices[i]), 2)
                amount = round(qty * selling_price, 2)
                points_earned = round(amount / 200, 2)
                points_earned_total += points_earned

                item_code = codes[i]
                remaining_qty = qty

                inventory_items = Inventory.objects.filter(
                    code=item_code,
                    quantity__gt=0
                ).order_by('purchased_at', 'id')

                item_inventory_details = []

                for inv_item in inventory_items:
                    if remaining_qty <= 0:
                        break                 

                    if "bulk" in inv_item.unit.lower():                        
                        available_qty = inv_item.split_unit or 0
                        deduct_qty = min(available_qty, remaining_qty)

                        unit_quantity = inv_item.unit_qty or 1
                        quantity_to_deduct = deduct_qty / unit_quantity

                        # inv_item.split_unit -= deduct_qty
                        new_split_unit = max(0, (inv_item.split_unit or 0) - deduct_qty)
                        inv_item.split_unit = new_split_unit

                        inv_item.quantity = round(inv_item.quantity - quantity_to_deduct, 1)

                        if (inv_item.split_unit is None or inv_item.split_unit <= 0) or (inv_item.quantity is None or inv_item.quantity <= 0):
                            inv_item.status = "completed"

                        inv_item.save()

                    else:
                        available_qty = inv_item.quantity
                        deduct_qty = min(available_qty, remaining_qty)

                        inv_item.quantity -= deduct_qty

                        if inv_item.quantity is None or inv_item.quantity <= 0:
                            inv_item.status = "completed"

                        inv_item.save()

                    remaining_qty -= deduct_qty

                if remaining_qty > 0:
                    raise ValueError(f"Insufficient stock for item {item_names[i]} (Code: {item_code})")

                # Save item to BillingItem table
                BillingItem.objects.create(
                    billing=billing,
                    customer=billing.customer,
                    code=codes[i],
                    item_name=item_names[i],
                    unit=units[i],
                    qty=qty,
                    mrp=mrp,
                    selling_price=selling_price,
                    amount=amount
                )

            # Update points after item processing
            billing.points = total_points + points_earned_total
            billing.points_earned = points_earned_total
            billing.save()
            
            return redirect('billing')

        except Exception as e:
            print(f"[ERROR] Invoice creation failed: {e}")
            return render(request, 'billing.html', {
                'error': 'Something went wrong while saving the invoice.'
            })

    # GET request for normal page
    latest_bill = Billing.objects.order_by('-id').first()
    next_bill_no = str(int(latest_bill.bill_no) + 1) if latest_bill and str(latest_bill.bill_no).isdigit() else '1'
    today_date = timezone.now().strftime('%Y-%m-%d')

    return render(request, 'billing.html', {
        'today_date': today_date,
        'bill_no': next_bill_no
    })

def get_item_info(request):
    code = request.GET.get('code', '').strip()
    name = request.GET.get('name', '').strip()

    # Step 1: Find the item
    item = None
    if code:
        item = Item.objects.filter(code__iexact=code).first()
    elif name:
        item = Item.objects.filter(item_name__iexact=name).first()

    if not item:
        return JsonResponse({'error': 'Item not found'}, status=404)

    is_bulk = 'bulk' in item.unit.lower()

    # Step 2: Get inventory in FIFO order
    inventory_qs = Inventory.objects.filter(
        code=item.code,
        status="in_stock"
    ).order_by('purchased_at', 'batch_no', 'id')

    if not inventory_qs.exists():
        return JsonResponse({
            'item_name': item.item_name,
            'item_code': item.code,
            'unit': item.unit,
            'is_bulk': is_bulk,
            'total_available': 0,
            'low_stock_warning': True,
            'warning_message': "⚠️ No stock available",
            'batch_details': [],
            'all_batch_nos': []
        })

    # Step 3: Find the first MRP available (FIFO)
    current_mrp = round(float(inventory_qs.first().mrp_price or 0), 2)

    total_available = 0
    low_stock_batches = []
    merged_batches = []
    all_batch_nos = []

    # Step 4: Loop and only process batches with the same MRP
    for inv in inventory_qs:
        batch_mrp = round(float(inv.mrp_price or 0), 2)
        if batch_mrp != current_mrp:
            break  # stop when MRP changes (FIFO)

        available = inv.split_unit if is_bulk else inv.quantity
        available = available or Decimal('0')

        total_available += available
        all_batch_nos.append(inv.batch_no)

        current_row = {
            'batch_no': inv.batch_no,
            'available_qty': float(available),
            'mrp': batch_mrp,
            'split_sale_price': round(float(inv.sale_price or 0), 2),
            'purchased_at': inv.purchased_at.strftime('%Y-%m-%d'),
            'status': inv.status,
        }

        # Merge if last batch has same MRP
        if merged_batches and merged_batches[-1]['mrp'] == batch_mrp:
            merged_batches[-1]['available_qty'] += current_row['available_qty']
            merged_batches[-1]['batch_no'] += f", {current_row['batch_no']}"
        else:
            merged_batches.append(current_row)

        if available < 10:
            low_stock_batches.append(inv.batch_no)

    # Step 5: Round quantities
    for batch in merged_batches:
        batch['available_qty'] = round(batch['available_qty'], 2)

    # Step 6: Set warnings
    low_stock_warning = bool(low_stock_batches)
    if total_available == 0:
        warning_message = "⚠️ No stock available"
    elif low_stock_warning:
        warning_message = f"⚠️ Low stock in batch(es): {', '.join(low_stock_batches)}, available qty: {round(total_available, 2)}"
    else:
        warning_message = ""

    return JsonResponse({
        'item_name': item.item_name,
        'item_code': item.code,
        'unit': item.unit,
        'is_bulk': is_bulk,
        'current_mrp': current_mrp,
        'total_available': round(total_available, 2),
        'low_stock_warning': low_stock_warning,
        'warning_message': warning_message,
        'batch_details': merged_batches,
        'all_batch_nos': all_batch_nos
    })
       
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
            email = request.POST.get('email')
            address = request.POST.get('address')
            date_joined = request.POST.get('date_joined')
            sale_type = request.POST.get('sale_type')
            bill_type = request.POST.get('bill_type')
            counter = request.POST.get('counter')            
            total_points = float(request.POST.get('points') or 0)
            earned_points = float(request.POST.get('total_earned') or 0)
            item_data_raw = request.POST.get('item_data')    

            item_data = json.loads(item_data_raw) if item_data_raw else []

            # Auto-generate quotation number
            latest = Quotation.objects.order_by('-id').first()
            base_qtn_no = int(latest.qtn_no) + 1 if latest and str(latest.qtn_no).isdigit() else 1
            qtn_no = str(base_qtn_no)

            quotation = Quotation.objects.create(
                qtn_no=qtn_no,
                date=date.today(),
                name=name,
                email=email,
                address=address,
                cell=cell,
                date_joined=date_joined,
                sale_type=sale_type,
                bill_type=bill_type,
                counter=counter,
                # order_no=order_no,
                # received=received,
                # balance=balance,
                points=total_points,
                points_earned=earned_points,
                items=item_data,
            )

            return JsonResponse({'success': True, 'quotation_id': quotation.id})

        except Exception as e:
            return JsonResponse({'success': False, 'error': f"Failed to save quotation. {str(e)}"})

    return redirect('quotation_detail', qtn_no=quotation.qtn_no)    

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
                'email': quotation.email,
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
        'email': last_quotation.email,
        'address': last_quotation.address,
        'sale_type': last_quotation.sale_type,
        'bill_type': last_quotation.bill_type,
        'counter': last_quotation.counter,
        'points': last_quotation.points,
        'points_earned': last_quotation.points_earned,
        'items': json.loads(last_quotation.items) if last_quotation.items else [],
    }
    
    return JsonResponse(data)

def update_payment(request, order_id):
    order = get_object_or_404(Order, pk=order_id)

    if request.method == "POST":
        try:
            paid_now = request.POST.get("paid_now")

            if paid_now:
                paid_now = Decimal(paid_now)
                order.paid_amount = paid_now

                total_paid = order.advance + paid_now
                order.due_balance = (order.total_order_amount - total_paid).quantize(Decimal("0.00"), rounding=ROUND_HALF_UP)

            else:
                 order.paid_amount = Decimal("0.00")
                 order.due_balance = (order.total_order_amount - order.advance).quantize(Decimal("0.00"), rounding=ROUND_HALF_UP)
                 order.order_status = 'completed' if order.due_balance <= 0 else 'pending'                
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

    # Create the Order
    order = Order.objects.create(
        customer_name=first_qtn.name,
        phone_number=first_qtn.cell,
        address=first_qtn.address,
        email=first_qtn.email,
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
            'email': first_qtn.email,
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
    status_on="order_bill"
    )

    # Process stock and Billing Items
    for item in items:
        qty = round(float(item.get("qty", 0)), 2)
        mrp = round(float(item.get("mrsp", 0)), 2)
        selling_price = round(float(item.get("sellingprice", 0)), 2)
        amount = round(qty * selling_price, 2)
        points_earned = round(amount / 200, 2)
        points_earned_total += points_earned

        item_code = item.get("code", "")
        remaining_qty = qty

        inventory_items = Inventory.objects.filter(
            code=item_code,
            quantity__gt=0
        ).order_by('purchased_at', 'id')

        for inv_item in inventory_items:
            if remaining_qty <= 0:
                break

            if "bulk" in inv_item.unit.lower():
                available_qty = inv_item.split_unit or 0
                deduct_qty = min(available_qty, remaining_qty)
                unit_quantity = inv_item.unit_qty or 1
                quantity_to_deduct = deduct_qty / unit_quantity
                inv_item.split_unit = max(0, (inv_item.split_unit or 0) - deduct_qty)
                inv_item.quantity = round(inv_item.quantity - quantity_to_deduct, 1)
            else:
                available_qty = inv_item.quantity
                deduct_qty = min(available_qty, remaining_qty)
                inv_item.quantity -= deduct_qty

            if (inv_item.split_unit is not None and inv_item.split_unit <= 0) or (inv_item.quantity is not None and inv_item.quantity <= 0):
                inv_item.status = "completed"

            inv_item.save()
            remaining_qty -= deduct_qty

        if remaining_qty > 0:
            raise ValueError(f"Insufficient stock for item {item.get('item_name', '')} (Code: {item_code})")

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

@access_required(allowed_roles=['superuser'])
def item_creation(request):  
    if request.method == "POST":
        code = request.POST.get('code')
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

        # Create the item
        Item.objects.create(
            code=code,
            status=status,
            item_name=item_name,
            print_name=print_name,
            unit=unit,
            P_unit=P_unit,
            group=group,
            brand=brand,
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
            min_stock=min_stock
        )
        return redirect('items')

    context = {
        'units': Unit.objects.all(),
        'brands': Brand.objects.all(),
        'groups': Group.objects.all(),
        'taxes': Tax.objects.all()
    }
    return render(request, 'items.html', context)

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

@access_required(allowed_roles=['superuser'])
def Item_barcode(request):
    if request.method == 'POST':
        barcode = request.POST.get('barcode')
        item_code = request.POST.get('item_code')
        item_name = request.POST.get('item_name')
        unit = request.POST.get('unit')
        mrp = request.POST.get('mrp')
        sale_price = request.POST.get('sale_price')
        whole_price = request.POST.get('whole_price')
        generated_on = request.POST.get('generated_on')
        active = True if request.POST.get('active') == 'on' else False
        
        ItemBarcode.objects.create(
            barcode=barcode,
            item_code=item_code,
            item_name=item_name,
            unit=unit,
            mrp=mrp,
            sale_price=sale_price,
            whole_price=whole_price,
            generated_on=generated_on,
            active=active
        )
        return redirect('item_barcode')
    
    return render(request,'barcode.html')

@access_required(allowed_roles=['superuser'])
def Unit_creation(request):
    if request.method == 'POST':
        unit_name = request.POST.get('unit_name')
        print_name = request.POST.get('print_name')
        decimals_raw = request.POST.get('decimals')
        UQC = request.POST.get('UQC')

        decimals = None if decimals_raw.strip() == "" else Decimal(decimals_raw)

        Unit.objects.create(
            unit_name=unit_name,
            print_name=print_name,
            decimals=decimals,
            UQC=UQC
        )
        return redirect('unit_creation')
    return render(request,'unit.html')

def Group_creation(request):
    if request.method == 'POST':
        group_name = request.POST.get('group_name')
        alias_name = request.POST.get('alias_name')
        under = request.POST.get('under')
        print_name = request.POST.get('print_name')
        commodity = request.POST.get('commodity')

        Group.objects.create(
            group_name=group_name,
            alias_name=alias_name,
            under=under,
            print_name=print_name,
            commodity=commodity
        )
        return redirect('group_creation')
    return render(request,'group.html')

@access_required(allowed_roles=['superuser'])
def Brand_creation(request):
    if request.method == 'POST':
        brand_name = request.POST.get('brand_name')
        alias_name = request.POST.get('alias_name')
        under = request.POST.get('under')
        print_name = request.POST.get('print_name')

        Brand.objects.create(
            brand_name=brand_name,
            alias_name=alias_name,
            under=under,
            print_name=print_name,
        )
        return redirect('brand_creation')
    return render(request,'brand.html')

@access_required(allowed_roles=['superuser'])
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


def sale_return_view(request):
    billing = None
    billing_items = []
    error = None

    # Initialize form fields variables to pass to template
    bill_no = ''
    customer_name = ''
    customer_phone = ''

    if request.method == "POST":
        if "fetch_bill" in request.POST:
            bill_no = request.POST.get("bill_no", "").strip()
            customer_name = request.POST.get("customer_name", "").strip()
            customer_phone = request.POST.get("customer_phone", "").strip()

            if not bill_no:
                error = "Please enter the Bill Number."
            else:
                billings = Billing.objects.filter(bill_no=bill_no)
                if customer_name or customer_phone:
                    billings = billings.filter(
                        Q(customer__name__icontains=customer_name) if customer_name else Q(),
                        Q(customer__cell__icontains=customer_phone) if customer_phone else Q()
                    )
                if billings.exists():
                    # Redirect to GET with params to avoid resubmission on refresh
                    params = f"?bill_no={bill_no}&customer_name={customer_name}&customer_phone={customer_phone}"
                    url = reverse('sale_return')
                    return redirect(url + params)
                else:
                    error = "No billing found matching the given criteria."

        elif "process_return" in request.POST:
            billing_id = request.POST.get("billing_id")
            return_reason = request.POST.get("return_reason", "").strip()
            billing = Billing.objects.get(id=billing_id)
            billing_items = BillingItem.objects.filter(billing_id=billing.id)

            # Create SaleReturn with temporary 0 values
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
                 
                    try:
                        # First: Try exact match (MRP + in_stock)
                        print(f"Debug: Searching Inventory with code={item.code}, mrp={item.mrp}, status='in_stock'")
                        inventory_item = Inventory.objects.filter(
                            code=item.code,
                            mrp_price=item.mrp,
                            status__iexact="in_stock"
                        ).order_by('-id').first()
                        print("Debug: Inventory found:", inventory_item)

                        if inventory_item:
                            # Update in_stock batch
                            if "bulk" in item.unit.lower():
                                bag_size = Decimal(str(inventory_item.unit_qty)) if inventory_item.unit_qty else Decimal('1.00')
                                qty_fraction = ret_qty / bag_size
                                inventory_item.quantity += float(qty_fraction)                               
                                inventory_item.split_unit += float(ret_qty)                                                                                          
                            else:
                                inventory_item.quantity += float(ret_qty)
                            inventory_item.save()

                        else:
                            # Second: Try MRP match + completed
                            completed_item = Inventory.objects.filter(
                                code=item.code,
                                mrp_price=item.mrp,
                                status__iexact="completed"
                            ).order_by('-id').first()

                            if completed_item:
                                if "bulk" in item.unit.lower():
                                    bag_size = Decimal(str(completed_item.unit_qty)) if completed_item.unit_qty else Decimal('1.00')
                                    qty_fraction = ret_qty / bag_size
                                    completed_item.quantity += float(qty_fraction)                                   
                                    completed_item.split_unit += float(ret_qty)                                                                  
                                else:
                                    completed_item.quantity += float(ret_qty)
                                completed_item.status = "in_stock"
                                completed_item.save()

                            else:
                                # Third: If no match by status, try any batch with same MRP regardless of status
                                any_mrp_match = Inventory.objects.filter(
                                    code=item.code,
                                    mrp=item.mrp
                                ).order_by('-id').first()

                                if any_mrp_match:
                                    if "bulk" in item.unit.lower():
                                        bag_size = Decimal(str(inventory_item.unit_qty)) if inventory_item.unit_qty else Decimal('1.00')
                                        qty_fraction = ret_qty / bag_size
                                        any_mrp_match.quantity += float(qty_fraction)
                                        any_mrp_match.split_unit += float(ret_qty)
                                    else:
                                        any_mrp_match.quantity += float(ret_qty)
                                    any_mrp_match.status = "in_stock"  # Force restock
                                    any_mrp_match.save()

                                else:
                                    # Create new batch
                                    Inventory.objects.create(
                                        code=item.code,
                                        item_name=item.item_name,
                                        unit=item.unit,
                                        mrp_price=item.mrp,
                                        quantity=float(ret_qty) if item.unit.lower() != "bulk" else (float(ret_qty) / (item.unit_qty or Decimal('1.00'))),
                                        split_unit=float(ret_qty) if item.unit.lower() == "bulk" else None,
                                        unit_qty=item.unit_qty,
                                        status="in_stock"
                                    )

                    except Exception as e:
                        print(f"Error while processing inventory return: {e}")

                    total_qty += ret_qty
                    total_amount += ret_amount

            sale_return.total_return_qty = total_qty
            sale_return.total_refund_amount = total_amount
            sale_return.save()

            return redirect(reverse('sale_return'))

    else:
        # GET request: populate billing data if query params are present
        bill_no = request.GET.get("bill_no", "").strip()
        customer_name = request.GET.get("customer_name", "").strip()
        customer_phone = request.GET.get("customer_phone", "").strip()

        if bill_no:
            billings = Billing.objects.filter(bill_no=bill_no)
            if customer_name or customer_phone:
                billings = billings.filter(
                    Q(customer__name__icontains=customer_name) if customer_name else Q(),
                    Q(customer__cell__icontains=customer_phone) if customer_phone else Q()
                )
            if billings.exists():
                billing = billings.first()
                billing_items = BillingItem.objects.filter(billing_id=billing.id)
            else:
                error = "No billing found matching the given criteria."

    # Fetch all sale returns to show list on same page or elsewhere
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    sale_returns = SaleReturn.objects.select_related('billing', 'customer')

    # Apply date filter if both dates are provided
    if start_date and end_date:
        start_date = parse_date(start_date)
        end_date = parse_date(end_date)
        if start_date and end_date:
            sale_returns = sale_returns.filter(created_at__date__range=(start_date, end_date))

    sale_returns = sale_returns.order_by('-created_at')
    # sale_returns = SaleReturn.objects.select_related('billing', 'customer').order_by('-created_at')

    context = {
        "billing": billing,
        "billing_items": billing_items,
        "error": error,
        "bill_no": bill_no,
        "customer_name": customer_name,
        "customer_phone": customer_phone,
        "sale_returns": sale_returns,
    }
    return render(request, "sale_return.html", context)

from django.contrib import messages

def sale_return_success_view(request):
    messages.success(request, "Sale return processed successfully.")    
    return redirect('sale_return')

def sale_return_detail(request, pk):
    sale_return = get_object_or_404(SaleReturn, pk=pk)   
    return render(request, 'sale_return_detail.html', {'sale_return': sale_return})

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
    
def products_view(request):
    query = request.GET.get('q', '').strip()
    selected_group = request.GET.get('group', '').strip()

    base_queryset = Product.objects.all()

    if query:
        base_queryset = base_queryset.filter(item__item_name__icontains=query)

    if selected_group:
        base_queryset = base_queryset.filter(item__group=selected_group)

    # Get unique product IDs by item code after filtering
    unique_ids = (
        base_queryset
        .values('item__code')
        .annotate(min_id=Min('id'))
        .values_list('min_id', flat=True)
    )

    items = Product.objects.filter(id__in=unique_ids).select_related('item', 'supplier')

    # Count the products for current filter
    product_count = items.count()

    # Get distinct groups for the dropdown
    groups = Product.objects.values_list('item__group', flat=True).distinct().order_by('item__group')

    return render(request, 'products.html', {
        'items': items,
        'query': query,
        'groups': groups,
        'selected_group': selected_group,
        'product_count': product_count,
    })

@access_required(allowed_roles=['superuser'])
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

@access_required(allowed_roles=['superuser'])
def purchase_list(request):
    supplier_id = request.GET.get('supplier')
    sort_order = request.GET.get('sort', 'desc')

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

    context = {
        'purchases': purchases,
        'supplier_ids': PurchaseItem.objects.values_list('supplier_id', flat=True).distinct(),
        'selected_supplier': supplier_id,
        'sort_order': sort_order,
    }
    return render(request, 'purchase_list.html', context)

def export_purchases(request):
    # Example: return CSV
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="purchases.csv"'
    response.write("id,supplier,amount\n")  # Just a test line
    return response

@access_required(allowed_roles=['superuser'])
def fetch_item(request):
    name = request.GET.get('name', '').strip()
    code = request.GET.get('code', '').strip()

    print(f"Fetching item - Name: '{name}', Code: '{code}'")

    item = None

    if code:
        item = Item.objects.filter(code__iexact=code).first()

    if not item and name:
        item = Item.objects.filter(
            Q(item_name__iexact=name) | Q(code__iexact=name)
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

@access_required(allowed_roles=['superuser'])
def purchase_return_view(request):
    suppliers = Supplier.objects.all()
    return render(request, 'purchase_return.html', {
        'suppliers': suppliers
    })

@access_required(allowed_roles=['superuser'])
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

@access_required(allowed_roles=['superuser'])
def fetch_purchase_items(request):
    invoice_number = request.GET.get('invoice_number')
    print("Invoice number received:", invoice_number)
    if not invoice_number:
        print("No invoice number provided in request.")
        return JsonResponse({'error': 'Invoice number is required'}, status=400)
    try:
        purchase = Purchase.objects.get(invoice_no=invoice_number)
        print("Purchase found:", purchase.id, purchase.invoice_no)
    except Purchase.DoesNotExist:
        print("No purchase found for invoice:", invoice_number)
        return JsonResponse({'error': 'Purchase not found'}, status=404)
    items = PurchaseItem.objects.filter(purchase_id=purchase.id)
    print("Number of items found:", items.count())
    items_data = []
    for item in items:
        print("Serializing item:", item.id, item.item_name, "Qty:", item.quantity)
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

    print("=== Purchase Data Debug ===")
    print("Amount Paid:", purchase.amount_paid)
    print("Outstanding:", purchase.outstanding_amount)
    print("Payment Mode:", purchase.payment_mode)
    print("Payment Rate:", purchase.payment_rate)
    print("Payment Ref:", purchase.payment_reference)
    print("===========================")

    print("Returning", len(items_data), "items for invoice:", invoice_number)
    return JsonResponse({'items': items_data,  'purchase': purchase_data})

@access_required(allowed_roles=['superuser'])
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

@access_required(allowed_roles=['superuser'])
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

@access_required(allowed_roles=['superuser'])
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

@access_required(allowed_roles=['superuser'])
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

@access_required(allowed_roles=['superuser'])
def inventory_view(request):
    query = request.GET.get('q', '').strip()

    # Exclude any unit that contains the word "bulk"
    items = Inventory.objects.select_related('item') \
        .exclude(item__unit__icontains='bulk') \
        .order_by('-id')

    if query:
        items = items.filter(
            Q(item__item_name__icontains=query) |
            Q(item__code__icontains=query) |
            Q(item__brand__icontains=query) |
            Q(item__unit__icontains=query)           
        )

    return render(request, 'inventory.html', {
        'items': items
    })

@access_required(allowed_roles=['superuser'])
def split_stock_page(request):
    queryset = Inventory.objects.filter(unit__icontains='bulk')

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

@access_required(allowed_roles=['superuser'])
def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    return render(request, 'product_detail.html', {'product': product})

@access_required(allowed_roles=['superuser'])
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

@access_required(allowed_roles=['superuser'])
def add_supplier(request):
    if request.method == 'POST':      

        Supplier.objects.create(
            supplier_id=request.POST.get('supplier_id'),
            name=request.POST.get('name'),
            contact_person=request.POST.get('contact_person'),
            phone=request.POST.get('phone'),
            email=request.POST.get('email'),
            address=request.POST.get('address'),
            gst_number=request.POST.get('gst_number'),
            pan_number=request.POST.get('pan_number'),
            credit_terms=request.POST.get('credit_terms'),
            opening_balance=request.POST.get('opening_balance') or 0,
            bank_name=request.POST.get('bank_name'),
            account_number=request.POST.get('account_number'),
            ifsc_code=request.POST.get('ifsc_code'),
            status = request.POST.get('status'),
            notes=request.POST.get('notes'),            
        )
        return redirect('suppliers')

    return render(request, 'add_supplier.html')

@access_required(allowed_roles=['superuser'])
def edit_supplier(request, supplier_id):
    supplier = get_object_or_404(Supplier, pk=supplier_id)

    if request.method == 'POST':
        supplier.supplier_id = request.POST.get('supplier_id')
        supplier.name = request.POST.get('name')
        supplier.contact_person = request.POST.get('contact_person')
        supplier.phone = request.POST.get('phone')
        supplier.email = request.POST.get('email')
        supplier.address = request.POST.get('address')
        supplier.gst_number = request.POST.get('gst_number')
        supplier.fssai_number = request.POST.get('fssai_number')
        supplier.pan_number = request.POST.get('pan_number')
        supplier.credit_terms = request.POST.get('credit_terms')
        supplier.opening_balance = request.POST.get('opening_balance') or 0
        supplier.bank_name = request.POST.get('bank_name')
        supplier.account_number = request.POST.get('account_number')
        supplier.ifsc_code = request.POST.get('ifsc_code')
        supplier.status = request.POST.get('status')
        supplier.notes = request.POST.get('notes')       
        supplier.save()
        return redirect('suppliers')
    return render(request, 'edit_supplier.html', {'supplier': supplier})

@access_required(allowed_roles=['superuser'])
def delete_supplier(request, supplier_id):
    supplier = get_object_or_404(Supplier, pk=supplier_id)
    supplier.delete()
    return redirect('suppliers')

from django.contrib.auth.decorators import login_required, user_passes_test

@login_required
@access_required(allowed_roles=['superuser'])
def customers_view(request):
    try:
        start_date = request.GET.get("start")
        end_date = request.GET.get("end")

        # Base QuerySets
        manual_qs = Customer.objects.filter(remarks="manual_entry")
        billing_qs = Customer.objects.filter(remarks="billing_entry")

        # Apply Date Filter
        if start_date and end_date:
            manual_qs = manual_qs.filter(date_joined__date__range=[start_date, end_date])
            billing_qs = billing_qs.filter(date_joined__date__range=[start_date, end_date])

        # Customers from Customer table (manual entries)
        customer_entries = manual_qs.order_by("-date_joined")

        # Customers from Billing table (unique by phone, grouped)
        billing_customers = (
            billing_qs
            .values("name", "cell", "address", "email")
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
    })
 
@access_required(allowed_roles=['superuser'])
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

@access_required(allowed_roles=['superuser'])
def payment_list_view(request):
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    payment_mode = request.GET.get('payment_mode')

    # Join customer table for name & phone
    billings = Billing.objects.select_related('customer').all().order_by('id')

    # Date filter
    if from_date and to_date:
        try:
            from_date_obj = datetime.datetime.strptime(from_date, '%Y-%m-%d')
            to_date_obj = datetime.datetime.strptime(to_date, '%Y-%m-%d')

            start_dt = datetime.datetime.combine(from_date_obj.date(), datetime.time.min)
            end_dt = datetime.datetime.combine(to_date_obj.date(), datetime.time.max)

            billings = billings.filter(date__range=(start_dt, end_dt))
        except Exception as e:
            print("Date Filter Error:", e)

    # Payment mode filter
    if payment_mode and payment_mode != 'all':
        billings = billings.filter(bill_type__iexact=payment_mode)

    return render(request, 'payments.html', {
        'billings': billings,
        'from_date': from_date,
        'to_date': to_date,
        'payment_mode': payment_mode,
    })

@access_required(allowed_roles=['superuser'])
def purchase_items_view(request):
    items = PurchaseItem.objects.select_related(
        "purchase",
        "purchase__supplier"
    ).all().order_by('id')

    return render(request, "purchase_items.html", {"items": items})

def purchase_payments_api(request, invoice_no):
    payments = PurchasePayment.objects.filter(invoice_no=invoice_no).order_by('payment_date')
    data = [
        {
            "payment_amount": str(p.payment_amount),
            "payment_mode": p.payment_mode,
            "payment_reference": p.payment_reference,
            "purchase_id": p.purchase.id,
            "payment_date": p.payment_date.strftime("%Y-%m-%d"),
            "supplier_id": p.supplier.supplier_id,
            "balance_amount": str(p.balance_amount),
            "total_amount": str(p.total_amount),
        }
        for p in payments
    ]
    return JsonResponse({"payments": data})

@access_required(allowed_roles=['superuser'])
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

@access_required(allowed_roles=['superuser'])
def expense_list(request):
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    category = request.GET.get('category')

    all_expenses = Expense.objects.all()

    if from_date:
        all_expenses = all_expenses.filter(datetime__date__gte=from_date)
    if to_date:
        all_expenses = all_expenses.filter(datetime__date__lte=to_date)

    if category and category != 'all':
        all_expenses = all_expenses.filter(category=category)

    all_expenses = all_expenses.order_by('-datetime')

    expenses_by_date = defaultdict(list)
    for expense in all_expenses:
        local_datetime = localtime(expense.datetime)
        date_key = local_datetime.strftime('%Y-%m-%d')
        expenses_by_date[date_key].append({
            'category': expense.get_category_display(),
            'detail': expense.category_detail,
            'datetime': local_datetime,
            'paid_to': expense.paid_to,
            'payment_mode': expense.paymentmode,
            'amount': expense.category_detail  
        })

    category_totals = defaultdict(float)
    if from_date or to_date:
        filtered_expenses = Expense.objects.all()
        if from_date:
            filtered_expenses = filtered_expenses.filter(datetime__date__gte=from_date)
        if to_date:
            filtered_expenses = filtered_expenses.filter(datetime__date__lte=to_date)

        for exp in filtered_expenses:
            try:
                category_totals[exp.get_category_display()] += float(exp.category_detail)
            except (ValueError, TypeError):
                pass 

    return render(request, 'expense_list.html', {
        'expenses_by_date': dict(expenses_by_date),
        'from_date': from_date,
        'to_date': to_date,
        'selected_category': category,
        'category_totals': dict(category_totals),
        'show_totals': bool(from_date or to_date),
    })

@access_required(allowed_roles=['superuser'])
def user_view(request):
    if request.method == "POST":
        data = request.POST
        user = User.objects.create_user(
            username=data['username'],
            email=data['email'],
            phone_number=data['phone_number'],
            role=data['role'],
            status=data['status'],
            password=data['password']
        )
        user.can_edit_bill = 'can_edit_bill' in data
        user.can_print_previous_bills = 'can_print_previous_bills' in data
        user.dashboard_access = 'dashboard_access' in data
        user.save()
        return redirect('user_list')

    return render(request, 'user.html')

def backup_company_details(instance, backup_dir):
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(backup_dir, f"company_details_{timestamp}.json")

    data = serialize('json', [instance])  
    with open(backup_file, 'w') as f:
        f.write(data)

    print(f"CompanyDetails backup saved at: {backup_file}")
