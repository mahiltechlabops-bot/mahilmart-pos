from django.shortcuts import render, redirect,  get_object_or_404, render
from django.contrib.auth import authenticate, login
from MahilMartPOS_App.models import Product
from .models import Supplier
from .forms import SupplierForm
from .models import Customer, Billing
from django.shortcuts import render
from django.shortcuts import redirect
from django.utils import timezone
from django.db.models import Min
from .models import User
from .forms import CompanySettingsForm
from django.contrib import messages
from .models import Item, ItemBarcode, Unit, Group, Brand

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

from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.db.models import Sum
from django.utils import timezone
from .models import Billing

def create_invoice_view(request):
    # Handle AJAX request for autofill
    if request.method == 'GET' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        phone = request.GET.get('phone')
        latest_bill = Billing.objects.filter(phone=phone).order_by('-id').first()
        total_earned = Billing.objects.filter(phone=phone).aggregate(total=Sum('points_earned'))['total'] or 0

        return JsonResponse({
            'name': latest_bill.name if latest_bill else '',
            'points': latest_bill.points if latest_bill else 0,
            'email': latest_bill.email if latest_bill else '',
            'address': latest_bill.address if latest_bill else '',
            'date_joined': latest_bill.date_joined.strftime('%Y-%m-%d') if latest_bill else '',
        })

    # Handle form submission
    if request.method == 'POST':
        try:
            latest_bill = Billing.objects.order_by('-id').first()
            next_bill_no = str(int(latest_bill.bill_no) + 1) if latest_bill and latest_bill.bill_no.isdigit() else '1'

            qty = int(request.POST.get('qty', 0))
            mrsp = float(request.POST.get('mrsp', 0))
            total_amount = qty * mrsp
            points_earned = total_amount / 200

            customer_phone = request.POST.get('phone')
            previous_billing = Billing.objects.filter(phone=customer_phone).order_by('-id').first()
            previous_points = previous_billing.points if previous_billing else 0.0
            total_points = previous_points + points_earned

            billing = Billing(
                to=request.POST.get('to'),
                name=request.POST.get('name'),
                phone=customer_phone,
                email=request.POST.get('email'),
                address=request.POST.get('address'),
                date_joined=request.POST.get('date_joined') or timezone.now(),
                bill_no=next_bill_no,
                date=timezone.now().date(),
                bill_type=request.POST.get('bill_type'),
                counter=request.POST.get('counter'),
                order_no=request.POST.get('order_no'),
                sale_type=request.POST.get('sale_type'),
                sno=int(request.POST.get('sno')) if request.POST.get('sno') else None,
                code=request.POST.get('code'),
                item_name=request.POST.get('item_name'),
                qty=qty,
                mrsp=mrsp,
                total_items=1,
                selling_price=mrsp,  # Assuming selling_price = mrsp; update logic if needed
                total_amount=total_amount,
                received=float(request.POST.get('received', 0)),
                balance=float(request.POST.get('balance', 0)),
                discount=float(request.POST.get('discount', 0)),
                points_earned=points_earned,
                points=total_points,
            )
            billing.save()
            return redirect('billing')

        except Exception as e:
            return render(request, 'billing.html', {
                'error': f"Error occurred: {str(e)}",
                'today_date': timezone.now().strftime('%Y-%m-%d'),
                'bill_no': next_bill_no
            })

    # For GET page render
    latest_bill = Billing.objects.order_by('-id').first()
    next_bill_no = str(int(latest_bill.bill_no) + 1) if latest_bill and latest_bill.bill_no.isdigit() else '1'
    today_date = timezone.now().strftime('%Y-%m-%d')

    return render(request, 'billing.html', {
        'today_date': today_date,
        'bill_no': next_bill_no
    })

# Create your views
def item_creation(request):  
    if request.method == "POST":
        code = request.POST.get('code')
        status = request.POST.get('status')
        item_name = request.POST.get('item_name')
        print_name = request.POST.get('print_name')

        # Safely fetch ForeignKey instances using get_object_or_404 or check
        unit_id = request.POST.get('unit')
        P_unit_id = request.POST.get('P_unit')
        group_id = request.POST.get('group')
        brand_id = request.POST.get('brand')        

        unit = get_object_or_404(Unit, id=unit_id) if unit_id else None
        P_unit = get_object_or_404(Unit, id=P_unit_id) if P_unit_id else None
        group = get_object_or_404(Group, id=group_id) if group_id else None
        brand = get_object_or_404(Brand, id=brand_id) if brand_id else None

        tax = request.POST.get('tax')
        HSN_SAC = request.POST.get('hsn_sac')
        use_MRP = request.POST.get('use_mrp') == "Yes"
        points = request.POST.get('points') or 0
        cess_per_qty = request.POST.get('cess_per_qty') or 0

        # Optional float conversion for numeric fields
        P_rate = request.POST.get('p_rate') or 0
        cost_rate = request.POST.get('cost_rate') or 0
        MRSP = request.POST.get('mrp') or 0
        sale_rate = request.POST.get('sale_rate') or 0
        whole_rate = request.POST.get('whole_rate') or 0
        whole_rate_2 = request.POST.get('whole_rate2') or 0
        min_stock = request.POST.get('min_stock') or 0

        # Save item
        Item.objects.create(
            code=code,
            status=status,
            item_name=item_name,
            print_name=print_name,
            unit=unit,
            P_unit=P_unit,
            group=group,
            brand=brand,
            tax=tax,
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
        return redirect('item_creation')

    # Render with dropdown options
    context = {
        'units': Unit.objects.all(),
        'brands': Brand.objects.all(),
        'groups': Group.objects.all()
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

def order_view(request):
    return render(request, 'order.html')

def products_view(request):
    return render(request, 'products.html')

def sale_return_view(request):
    return render(request, 'sale_return.html')

def purchase_view(request):
    suppliers = Supplier.objects.all()
    return render(request, 'purchase.html', {
        'suppliers': suppliers
    })

def purchase_return_view(request):
    suppliers = Supplier.objects.all()
    return render(request, 'purchase_return.html', {
        'suppliers': suppliers
    })

def stock_adjustment_view(request):
    products = Product.objects.all()
    return render(request, 'stock_adjustment.html', {'products': products})

def inventory_view(request):
    from .models import Product, Category

    q = request.GET.get('q')
    category_id = request.GET.get('category')

    products = Product.objects.all()

    if category_id:
        products = products.filter(category_id=category_id)
    if q:
        products = products.filter(name__icontains=q)

    categories = Category.objects.all()

    return render(request, 'inventory.html', {
        'products': products,
        'categories': categories
    })

def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    return render(request, 'product_detail.html', {'product': product})

def suppliers_view(request):
    suppliers = Supplier.objects.all()
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
            name=request.POST.get('name'),
            contact_person=request.POST.get('contact_person'),
            phone=request.POST.get('phone'),
            email=request.POST.get('email'),
            address=request.POST.get('address'),
        )
        return redirect('suppliers')
    return render(request, 'add_supplier.html')

def customers_view(request):
    try:
        # Customers from Customer table
        customer_entries = Customer.objects.all().order_by('-date_joined')

        # Customers from Billing table (unique by phone, grouped)
        billing_customers = (
            Billing.objects
            .values('name', 'phone', 'address', 'email')
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
        phone = request.POST.get('phone')
        address = request.POST.get('address')
        email = request.POST.get('email')

        Customer.objects.create(
            name=name,
            phone=phone,
            address=address,
            email=email,
            date_joined=timezone.now()
        )

        return redirect('customers')

    return render(request, 'add_customer.html')

def submit_customer(request):
    if request.method == 'POST':
        name = request.POST['customer_name']
        phone = request.POST['phone_number']
        address = request.POST['address']
        email = request.POST.get('email')
        date_joined = request.POST.get('date_joined')

        Customer.objects.create(
            name=name,
            phone_number=phone,
            address=address,
            email=email,
            date_joined=date_joined
        )

    return redirect('customers')

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