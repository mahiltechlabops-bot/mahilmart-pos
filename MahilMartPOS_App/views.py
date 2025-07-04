from django.shortcuts import render,get_object_or_404, redirect, render
from django.contrib.auth import authenticate, login
from django.http import HttpResponse


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

def user_view(request):
    return render(request, 'user.html')
