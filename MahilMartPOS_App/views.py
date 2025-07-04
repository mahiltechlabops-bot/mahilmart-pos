from django.shortcuts import render, redirect,  get_object_or_404, render
from django.contrib.auth import authenticate, login
from MahilMartPOS_App.models import Product
from .models import Supplier
from .forms import SupplierForm


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

def order_view(request):
    return render(request, 'order.html')

def products_view(request):
    return render(request, 'products.html')

def sale_return_view(request):
    return render(request, 'sale_return.html')

def purchase_view(request):
    return render(request, 'purchase.html')

def purchase_return_view(request):
    return render(request, 'purchase_return.html')

def stock_adjustment_view(request):
    return render(request, 'stock_adjustment.html')

def inventory_view(request):
    query = request.GET.get('q')
    products = Product.objects.all()
    if query:
        products = products.filter(name__icontains=query)
    return render(request, 'inventory.html', {'products': products})

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

def user_view(request):
    return render(request, 'user.html')
