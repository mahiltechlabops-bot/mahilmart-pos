import json
import os,datetime
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
from .models import (
    Supplier,
    Customer,
    Billing,
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
    Quotation
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

def dashboard_view(request):
    return render(request, 'dashboard.html') 

def create_invoice_view(request):
    if request.method == 'GET' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        phone = request.GET.get('phone')
        latest_bill = Billing.objects.filter(cell=phone).order_by('-id').first()
        return JsonResponse({
            'name': latest_bill.name if latest_bill else '',
            'points': latest_bill.points if latest_bill else 0,
            'email': latest_bill.email if latest_bill else '',
            'address': latest_bill.address if latest_bill else '',
            'date_joined': str(latest_bill.date_joined) if latest_bill and latest_bill.date_joined else '',
        })

    if request.method == 'POST':
        cell = request.POST.get('cell')

        latest = Billing.objects.order_by('-id').first()
        base_bill_no = int(latest.bill_no) + 1 if latest and str(latest.bill_no).isdigit() else 1
        bill_no = str(base_bill_no)

        snos = request.POST.getlist('sno')
        codes = request.POST.getlist('code')
        item_names = request.POST.getlist('item_name')
        qtys = request.POST.getlist('qty')
        mrsps = request.POST.getlist('mrsp')
        selling_prices = request.POST.getlist('sellingprice')

        previous_bill = Billing.objects.filter(cell=cell).order_by('-id').first()
        total_points = previous_bill.points if previous_bill else 0.0

        for i in range(len(item_names)):
            if not any([
                codes[i].strip(),
                item_names[i].strip(),
                qtys[i].strip(),
                selling_prices[i].strip()
                ]):
                continue

            try:
                qty = int(qtys[i]) if qtys[i] else 0
                mrsp = float(mrsps[i]) if mrsps[i] else 0.0
                selling_price = float(selling_prices[i]) if selling_prices[i] else 0.0
                amount = qty * selling_price
                points_earned = amount / 200
                total_points += points_earned
                
                Billing.objects.create(
                    sno=int(snos[i]) if snos[i] else i + 1,
                    code=codes[i],
                    item_name=item_names[i],
                    qty=qty,
                    mrsp=mrsp,
                    selling_price=selling_price,
                    total_amount=amount,
                    points_earned=points_earned,
                    points=total_points,
                    to=request.POST.get('to'),
                    bill_no=bill_no,
                    date=timezone.now().date(),
                    name=request.POST.get('name'),
                    email=request.POST.get('email'),
                    address=request.POST.get('address'),
                    date_joined=request.POST.get('date_joined') or timezone.now().date(),
                    bill_type=request.POST.get('bill_type'),
                    sale_type=request.POST.get('sale_type'),
                    counter=request.POST.get('counter'),
                    order_no=request.POST.get('order_no'),
                    cell=cell,
                    received=request.POST.get('received') or 0,
                    balance=request.POST.get('balance') or 0,
                    discount=request.POST.get('discount') or 0,
                )
            except IntegrityError as e:
                print(f"Bill number conflict: {e}")
                base_bill_no += 1
                bill_no = str(base_bill_no)
                continue
            except Exception as e:
                print(f"Error in row {i+1}: {e}")
                continue

        return redirect('billing')

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

    item = None
    if code:
        item = Item.objects.filter(code__iexact=code).first()
    elif name:
        item = Item.objects.filter(item_name__iexact=name).first()
        
    if item:
        return JsonResponse({
            'item_name': item.item_name,
            'item_code': item.code,
            'mrsp': item.MRSP,
            'sale_rate': item.sale_rate,
        })
    else:
        return JsonResponse({'error': 'Item not found'}, status=404)

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

from django.shortcuts import redirect
from django.http import HttpResponse
from django.utils import timezone
from .models import Quotation
import logging

logger = logging.getLogger(__name__)

def create_quotation(request):
    if request.method == 'POST':
        try:
            # Get customer details from form fields
            name = request.POST.get('name')
            email = request.POST.get('email')
            cell = request.POST.get('cell')
            address = request.POST.get('address')
            bill_type = request.POST.get('bill_type')
            sale_type = request.POST.get('sale_type')
            counter = request.POST.get('counter')
            order_no = request.POST.get('order_no')
            date_joined = request.POST.get('date_joined') or timezone.now().date()

            logger.info(f"Received quotation from {name}, Phone: {cell}")

            # Generate quotation number
            latest = Quotation.objects.order_by('-id').first()
            base_qtn_no = int(latest.qtn_no) + 1 if latest and str(latest.qtn_no).isdigit() else 1
            qtn_no = str(base_qtn_no)

            # Get lists of item data
            snos = request.POST.getlist('sno')
            codes = request.POST.getlist('code')
            item_names = request.POST.getlist('item_name')
            qtys = request.POST.getlist('qty')
            mrsps = request.POST.getlist('mrsp')
            selling_prices = request.POST.getlist('sellingprice')

            for i in range(len(item_names)):
                if not item_names[i].strip():
                    continue  # Skip empty rows

                qty = int(qtys[i]) if qtys[i] else 0
                mrsp = float(mrsps[i]) if mrsps[i] else 0.0
                selling_price = float(selling_prices[i]) if selling_prices[i] else 0.0
                amount = qty * selling_price

                Quotation.objects.create(
                    sno=int(snos[i]) if snos[i] else i + 1,
                    qtn_no=qtn_no,
                    date=timezone.now().date(),
                    code=codes[i],
                    item_name=item_names[i],
                    qty=qty,
                    mrsp=mrsp,
                    selling_price=selling_price,
                    total_amount=amount,
                    name=name,
                    email=email,
                    address=address,
                    date_joined=date_joined,
                    bill_type=bill_type,
                    sale_type=sale_type,
                    counter=counter,
                    order_no=order_no,
                    cell=cell,
                )

            return redirect('quotation_detail', qtn_no=qtn_no)

        except Exception as e:
            logger.exception("Error while creating quotation")
            return HttpResponse("Internal server error", status=500)

    return HttpResponse("Method not allowed", status=405)

def quotation_detail(request, qtn_no):
    quotation_items = Quotation.objects.filter(qtn_no=qtn_no)
    if not quotation_items.exists():
        return HttpResponse("Quotation not found") 
    
    quotation = quotation_items.first()

    context = {
        'qtn_no': qtn_no,
        'customer': quotation,        
        'items': quotation_items,    
        'quotation': quotation        
    }
    return render(request, 'quotation_detail.html', context)

def update_payment(request, order_id):
    order = get_object_or_404(Order, pk=order_id)

    if request.method == "POST":
        try:
            paid_now = request.POST.get("paid_now")

            if paid_now:
                paid_now = Decimal(paid_now)
                order.advance += paid_now
                order.due_balance = (order.total_order_amount - order.advance).quantize(Decimal("0.00"), rounding=ROUND_HALF_UP)

                request.session['paid_now'] = str(paid_now)

            else:
                advance = Decimal(request.POST.get("advance", "0"))
                due_balance = Decimal(request.POST.get("due_balance", "0"))
                order.advance = advance
                order.due_balance = due_balance

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

def convert_quotation_to_order(request, qtn_no):
    quotations = Quotation.objects.filter(qtn_no=qtn_no)
    if not quotations.exists():
        return HttpResponse("Quotation not found") 

    first_qtn = quotations.first()

    order = Order.objects.create(
        customer_name=first_qtn.name,
        phone_number=first_qtn.cell,
        address=first_qtn.address,
        email=first_qtn.email,
        date_of_order=timezone.now(),
        expected_delivery_datetime=timezone.now(), 
        delivery='no', 
        charges=0,
        total_order_amount=sum(q.total_amount for q in quotations),
        advance=first_qtn.received,
        due_balance=first_qtn.balance,
        payment_type='cash',  
        order_status='pending',  
    )

    for q in quotations:
        OrderItem.objects.create(
            order=order,
            item_name=q.item_name,
            quantity=q.qty,
            rate=q.selling_price,
            amount=q.total_amount,
        )

    return redirect('order_list')

# Create your views
def item_creation(request):  
    if request.method == "POST":
        code = request.POST.get('code')
        status = request.POST.get('status')
        item_name = request.POST.get('item_name')
        print_name = request.POST.get('print_name')

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
            tax=gst_percent,  # Save the gst_percent directly
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

def Unit_creation(request):
    if request.method == 'POST':
        unit_name = request.POST.get('unit_name')
        print_name = request.POST.get('print_name')
        decimals = request.POST.get('decimals')
        UQC = request.POST.get('UQC')

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

def products_view(request):
    query = request.GET.get('q', '').strip()

    # Get unique product IDs by item code
    base_queryset = Product.objects.all()
    if query:
        base_queryset = base_queryset.filter(item__item_name__icontains=query)

    unique_ids = (
        base_queryset
        .values('item__code')
        .annotate(min_id=Min('id'))
        .values_list('min_id', flat=True)
    )

    items = Product.objects.filter(id__in=unique_ids).select_related('item', 'supplier')

    return render(request, 'products.html', {
        'items': items,
        'query': query
    })

def sale_return_view(request):
    return render(request, 'sale_return.html')

def purchase_view(request):
    if request.method == 'POST':
        supplier_id = request.POST.get('supplier')
        supplier = get_object_or_404(Supplier, id=supplier_id)
        purchase = Purchase.objects.create(supplier=supplier)

        rows = zip(
            request.POST.getlist('item_code'),
            request.POST.getlist('qty'),
            request.POST.getlist('price'),
            request.POST.getlist('discount'),
            request.POST.getlist('tax'),
            request.POST.getlist('mrp'),
            request.POST.getlist('whole_price'),
            request.POST.getlist('whole_price1'),
            request.POST.getlist('sale_price'),
        )

        for code, qty, price, disc, tax, mrp, wp, wp1, sp in rows:
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
            'group': item.group or '',
            'brand': item.brand or '',
            'unit': item.unit or '',
            'tax': item.tax,
            'wholesale': item.whole_rate,
            'wholesale_1': item.whole_rate_2,
            'sale_price': item.sale_rate,
            'mrp': item.MRSP,
        })

    return JsonResponse({'error': 'Item not found'}, status=404)

def purchase_return_view(request):
    suppliers = Supplier.objects.all()
    return render(request, 'purchase_return.html', {
        'suppliers': suppliers
    })

@csrf_exempt
def create_purchase(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            supplier_id = data.get("supplier_id")          
            items_data = data.get("items", [])

            supplier = Supplier.objects.get(id=supplier_id)
            # purchase = Purchase.objects.create(supplier=supplier)    
            invoice_no = data.get("invoice_no", "").strip()
            purchase = Purchase.objects.create(supplier=supplier, invoice_no=invoice_no)                

            # Track quantities during this request
            latest_qty_cache = {}

            for item in items_data:
                item_code = item.get('item_code')
                item_obj = Item.objects.filter(code=item_code).first()
                if not item_obj:
                    continue

                item_id = item_obj.id
                qty_purchased = float(item['quantity'])

                # Fetch previous quantity
                if item_id in latest_qty_cache:
                    previous_qty = latest_qty_cache[item_id]
                else:
                    last = PurchaseItem.objects.filter(item=item_obj).order_by('-id').first()
                    previous_qty = float(last.total_qty) if last else 0

                total_qty = previous_qty + qty_purchased

                # Update in-memory cache
                latest_qty_cache[item_id] = total_qty

                # Save purchase item with correct qtys
                PurchaseItem.objects.create(
                    purchase=purchase,
                    item=item_obj,                  
                    group=item_obj.group,
                    brand=item_obj.brand,
                    unit=item_obj.unit,
                    code=item.get('item_code', ''),
                    item_name=item.get('item_name', ''),                   
                    quantity=qty_purchased,
                    unit_price=item['price'],
                    total_price=item['total_price'],
                    discount=item['discount'],
                    tax=item['tax'],
                    net_price=item['net_price'],
                    mrp_price=item['mrp'],
                    whole_price=item['whole_price'],
                    whole_price_2=item['whole_price_2'],
                    sale_price=item['sale_price'],        
                    supplier_id=supplier.supplier_id,
                    purchased_at=parse_date(item.get('purchased_at')),
                    batch_no=item.get('batch_no', ''),
                    expiry_date=parse_date(item.get('expiry_date')),
                    previous_qty=previous_qty,
                    total_qty=total_qty
                )

                Inventory.objects.create(
                    item=item_obj,
                    item_name=item.get('item_name', ''),
                    code=item.get('item_code', ''),
                    group=item_obj.group,
                    brand=item_obj.brand,
                    unit=item_obj.unit,
                    batch_no=item.get('batch_no', ''),
                    invoice_no=item.get('invoice_no', ''),                   
                    supplier=supplier,
                    quantity=qty_purchased,
                    previous_qty=previous_qty,
                    total_qty=total_qty,
                    unit_price=item['price'],
                    total_price=item['total_price'],
                    discount=item['discount'],
                    tax=item['tax'],
                    net_price=item['net_price'],
                    mrp_price=item['mrp'],
                    whole_price=item['whole_price'],
                    whole_price_2=item['whole_price_2'],
                    sale_price=item['sale_price'],
                    purchased_at=parse_date(item.get('purchased_at')),
                    expiry_date=parse_date(item.get('expiry_date')),
                    purchase=purchase
                )

                # Optional product snapshot
                Product.objects.create(
                    supplier=supplier,
                    item=item_obj,
                    item_name=item_obj.item_name,
                    code=item_obj.code,
                    group=item_obj.group,
                    brand=item_obj.brand,
                    unit=item_obj.unit,
                    mrp=item_obj.MRSP,
                    whole_rate=item_obj.whole_rate,
                    whole_rate_2=item_obj.whole_rate_2,
                    sale_rate=item_obj.sale_rate
                )

            return JsonResponse({'success': True})

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    return JsonResponse({'error': 'Invalid method'}, status=405)

@csrf_exempt
def stock_adjustment_view(request):
    # Unique products (for dropdown)
    unique_products = (
        PurchaseItem.objects
        .filter(item_name__isnull=False)
        .order_by('item_name', 'id')
        .distinct('item_name')
    )

    # All products with batch info
    products = PurchaseItem.objects.filter(item_name__isnull=False)

    if request.method == "POST":
        product_id = request.POST.get("product")
        adjustment_type = request.POST.get("adjustmentType")
        quantity = request.POST.get("quantity")
        reason = request.POST.get("reason")
        remarks = request.POST.get("remarks")

        # Validate required fields
        if not all([product_id, adjustment_type, quantity]):
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
        else:
            messages.error(request, "Invalid adjustment type.")
            return redirect('stock_adjustment')   
        
        StockAdjustment.objects.create(
            purchase_item=selected_batch,       
            batch_no=selected_batch.batch_no,
            code=selected_batch.code,
            item_name=selected_batch.item_name,          
            supplier_code=selected_batch.purchase.supplier.supplier_id,          
            adjustment_type=adjustment_type,
            quantity=quantity,
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

        messages.success(
            request,
            f"Stock successfully adjusted: {adjustment_type.upper()} {quantity} units for '{selected_batch.item_name}' (Batch {selected_batch.batch_no})."
        )
        return redirect('stock_adjustment')

    return render(request, "stock_adjustment.html", {
        "products": products,
        "unique_products": unique_products
    })

def stock_adjustment_list(request):
    adjustments = StockAdjustment.objects.all().order_by('-adjusted_at')
    return render(request, 'stock_adjustment_list.html', {'adjustments': adjustments})

def edit_bulk_item(request, item_id):
    bulk_item = get_object_or_404(PurchaseItem, id=item_id)

    if request.method == 'POST':
        print("POST request received:", request.POST)

        try:
            purchased_at = request.POST.get('purchased_at')
            expiry_date = request.POST.get('expiry_date')

            purchased_at_date = datetime.strptime(purchased_at, '%Y-%m-%d').date() if purchased_at else None
            expiry_date_date = datetime.strptime(expiry_date, '%Y-%m-%d').date() if expiry_date else None

            # Get supplier by code if needed
            try:
                supplier_obj = Supplier.objects.get(code=bulk_item.supplier_id)
            except Supplier.DoesNotExist:
                messages.error(request, "Supplier not found")
                return render(request, 'edit_bulk_item.html', {'item': bulk_item})

            inventory = Inventory(
                item=bulk_item.item,
                item_name=request.POST.get('item_name'),
                code=request.POST.get('code'),
                group=request.POST.get('group'),
                brand=request.POST.get('brand'),
                unit=request.POST.get('unit'),
                batch_no=request.POST.get('batch_no'),
                invoice_no=request.POST.get('invoice_no'),
                quantity=float(request.POST.get('quantity') or 0),
                previous_qty=float(request.POST.get('previous_qty') or 0),
                total_qty=float(request.POST.get('total_qty') or 0),
                unit_price=float(request.POST.get('unit_price') or 0),
                total_price=float(request.POST.get('total_price') or 0),
                discount=float(request.POST.get('discount') or 0),
                tax=float(request.POST.get('tax') or 0),
                net_price=float(request.POST.get('net_price') or 0),
                mrp_price=float(request.POST.get('mrp_price') or 0),
                whole_price=float(request.POST.get('whole_price') or 0),
                whole_price_2=float(request.POST.get('whole_price_2') or 0),
                sale_price=float(request.POST.get('sale_price') or 0),
                purchased_at=purchased_at_date,
                expiry_date=expiry_date_date,
                supplier=supplier_obj,
                purchase=bulk_item.purchase
            )
            inventory.save()
            print("Inventory saved with ID:", inventory.id)

            messages.success(request, "Item added to inventory successfully.")
            return redirect('split_stock')

        except Exception as e:
            print("Save error:", e)
            messages.error(request, f"Error saving to inventory: {e}")

    return render(request, 'edit_bulk_item.html', {'item': bulk_item})

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

def split_stock_page(request):
    bulk_items = PurchaseItem.objects.filter(unit__icontains='bulk')
    return render(request, 'split_stock.html', {'bulk_items': bulk_items})
   

def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    return render(request, 'product_detail.html', {'product': product})

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
            notes=request.POST.get('notes'),
        )
        return redirect('suppliers')
    return render(request, 'add_supplier.html')

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
        supplier.pan_number = request.POST.get('pan_number')
        supplier.credit_terms = request.POST.get('credit_terms')
        supplier.opening_balance = request.POST.get('opening_balance') or 0
        supplier.bank_name = request.POST.get('bank_name')
        supplier.account_number = request.POST.get('account_number')
        supplier.ifsc_code = request.POST.get('ifsc_code')
        supplier.notes = request.POST.get('notes')
        supplier.save()
        return redirect('suppliers')
    return render(request, 'edit_supplier.html', {'supplier': supplier})

def delete_supplier(request, supplier_id):
    supplier = get_object_or_404(Supplier, pk=supplier_id)
    supplier.delete()
    return redirect('suppliers')

def customers_view(request):
    try:
        # Customers from Customer table
        customer_entries = Customer.objects.all().order_by('-date_joined')

        # Customers from Billing table (unique by phone, grouped)
        billing_customers = (
            Billing.objects
            .values('name', 'cell', 'address', 'email')
            .annotate(date_joined=Min('date_joined'))
            .order_by('-date_joined')
        )

    except Exception as e:
        from django.http import HttpResponse
        return HttpResponse("Error: " + str(e))

    return render(request, 'customers.html', {
        'customer_entries': customer_entries,
        'billing_customers': billing_customers
    })
 
def add_customer(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        cell = request.POST.get('cell')
        address = request.POST.get('address')
        email = request.POST.get('email')

        Customer.objects.create(
            name=name,
            cell=cell,
            address=address,
            email=email,
            date_joined=timezone.now()
        )

        return redirect('customers')

    return render(request, 'add_customer.html')

def submit_customer(request):
    if request.method == 'POST':
        name = request.POST['customer_name']
        cell = request.POST['phone_number']
        address = request.POST['address']
        email = request.POST.get('email')
        date_joined = request.POST.get('date_joined')

        Customer.objects.create(
            name=name,
            phone_number=cell,
            address=address,
            email=email,
            date_joined=date_joined
        )

    return redirect('customers')

def payments_view(request):
    return render(request, 'payments.html')

def payment_list_view(request):
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    payment_mode = request.GET.get('payment_mode')

    billings = Billing.objects.all().order_by('id')

    if from_date and to_date:
        try:
            from_date_obj = datetime.datetime.strptime(from_date, '%Y-%m-%d').date()
            to_date_obj = datetime.datetime.strptime(to_date, '%Y-%m-%d').date()
            billings = billings.filter(date__range=(from_date_obj, to_date_obj))
        except Exception as e:
            print("Date Filter Error:", e)

    if payment_mode and payment_mode != 'all':
        billings = billings.filter(bill_type__iexact=payment_mode)

    return render(request, 'payments.html', {
        'billings': billings,
        'from_date': from_date,
        'to_date': to_date,
        'payment_mode': payment_mode,
    })

def purchase_items_view(request):
    if request.method == 'POST':
        return redirect('payment_list')  
    return render(request, 'purchase_items.html')

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

def view_company_details(request):
    company = CompanyDetails.objects.last()
    return render(request, 'view_company_details.html', {'company': company})
