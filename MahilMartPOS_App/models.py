from datetime import date
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager, Group, Permission

class Category(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name
   
class Supplier(models.Model):
    supplier_id = models.CharField(max_length=50, unique=True, null=True, blank=True)
    name = models.CharField(max_length=100)
    contact_person = models.CharField(max_length=100, blank=True, default="Unknown")
    phone = models.CharField(max_length=15, default="0000000000")
    email = models.EmailField(blank=True, default="unknown@example.com")
    address = models.TextField(blank=True, default="N/A")
    gst_number = models.CharField(max_length=20, blank=True, default="N/A")
    pan_number = models.CharField(max_length=20, blank=True, default="N/A")
    credit_terms = models.CharField(max_length=50, blank=True, default="N/A")
    opening_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    bank_name = models.CharField(max_length=100, blank=True, default="N/A")
    account_number = models.CharField(max_length=50, blank=True, default="N/A")
    ifsc_code = models.CharField(max_length=20, blank=True, default="N/A")
    notes = models.TextField(blank=True, default="")

    def __str__(self):
        return self.name    

class Customer(models.Model):
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    date_joined = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.phone})"        

class Billing(models.Model):
    to = models.CharField(max_length=100, blank=True, null=True)
    name = models.TextField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)

    email = models.EmailField(blank=True, null=True)          
    address = models.TextField(blank=True, null=True)          
    date_joined = models.DateTimeField(default=timezone.now)  

    bill_no = models.CharField(max_length=20, unique=True)
    date = models.DateField()
    bill_type = models.CharField(max_length=20, blank=True, null=True)  
    counter = models.CharField(max_length=50,  blank=True, null=True)
    order_no = models.CharField(max_length=50, blank=True, null=True)
    sale_type = models.CharField(max_length=20,  blank=True, null=True)
    sno = models.IntegerField(null=True, blank=True)
    code = models.CharField(max_length=50)
    item_name = models.CharField(max_length=100)
    qty = models.PositiveIntegerField()
    mrsp = models.DecimalField(max_digits=10, decimal_places=2)
    total_items = models.PositiveIntegerField(default=1)
    selling_price = models.FloatField(default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    received = models.DecimalField(max_digits=10, decimal_places=2)
    balance = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    points = models.FloatField(default=0.0)  
    points_earned = models.FloatField(default=0.0)

    def __str__(self):
        return f"Invoice {self.bill_no} - {self.item_name}"
    

class Order(models.Model):
    DELIVERY_CHOICES = [
        ('yes', 'Yes'),
        ('no', 'No'),
    ]

    PAYMENT_TYPE_CHOICES = [
        ('cash', 'Cash'),
        ('gpay', 'GPay'),
        ('card', 'Card'),
        ('credit', 'Credit'),
    ]

    ORDER_STATUS_CHOICES = [
        ('completed', 'Completed'),
        ('pending', 'Pending'),
        ('elapsed', 'Elapsed'),
        ('cancelled', 'Cancelled'),
    ]

    order_id = models.AutoField(primary_key=True)
    customer_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=10)
    address = models.TextField()
    email = models.EmailField()

    date_of_order = models.DateTimeField(default=timezone.now)
    expected_delivery_datetime = models.DateTimeField()

    delivery = models.CharField(max_length=3, choices=DELIVERY_CHOICES)
    charges = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    total_order_amount = models.DecimalField(max_digits=10, decimal_places=2)
    advance = models.DecimalField(max_digits=10, decimal_places=2)
    due_balance = models.DecimalField(max_digits=10, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    payment_type = models.CharField(max_length=10, choices=PAYMENT_TYPE_CHOICES)
    order_status = models.CharField(max_length=10, choices=ORDER_STATUS_CHOICES)

    def save(self, *args, **kwargs):
        if self.advance >= self.total_order_amount:
            self.full_amount_paid = True
        else:
            self.full_amount_paid = False
        self.due_balance = self.total_order_amount - self.advance
        super().save(*args, **kwargs)
        
    def __str__(self):
        return f"Order #{self.order_id} - {self.customer_name}"

class Quotation(models.Model):
    sno = models.IntegerField()
    qtn_no = models.CharField(max_length=100)
    code = models.CharField(max_length=100)
    item_name = models.CharField(max_length=200)
    qty = models.IntegerField()
    mrsp = models.FloatField()
    selling_price = models.FloatField()
    total_amount = models.FloatField()
    points_earned = models.FloatField(default=0)
    to = models.CharField(max_length=100)
    bill_no = models.CharField(max_length=20)
    date = models.DateField()
    name = models.CharField(max_length=100)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    date_joined = models.DateField()
    bill_type = models.CharField(max_length=100)
    sale_type = models.CharField(max_length=100)
    counter = models.CharField(max_length=100)
    order_no = models.CharField(max_length=100, blank=True)
    cell = models.CharField(max_length=20)
    received = models.FloatField(default=0)
    balance = models.FloatField(default=0)
    discount = models.FloatField(default=0)    

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    item_name = models.CharField(max_length=100)
    quantity = models.PositiveIntegerField()
    rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    amount = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return self.item_name          
    
class Item(models.Model):
    code = models.CharField(max_length=30)
    item_name = models.CharField(max_length=50)
    print_name = models.CharField(max_length=50, blank=True, null=True)
    status = models.CharField(max_length=10)
    unit = models.CharField(max_length=20, blank=True, null=True)
    P_unit = models.CharField(max_length=20, blank=True, null=True)
    group = models.CharField(max_length=100, blank=True, null=True)
    brand = models.CharField(max_length=100, blank=True, null=True)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    HSN_SAC = models.IntegerField(blank=True, null=True)
    P_rate = models.IntegerField()
    cost_rate = models.IntegerField()
    MRSP = models.IntegerField()
    sale_rate = models.IntegerField()
    whole_rate = models.IntegerField()
    whole_rate_2 = models.IntegerField()
    use_MRP = models.CharField(max_length=10)
    min_stock = models.CharField(max_length=100)
    stock_item = models.CharField(max_length=10)
    carry_over = models.CharField(max_length=10)
    manual = models.CharField(max_length=10)
    points = models.IntegerField()
    cess_per_qty =  models.IntegerField()
    picture = models.ImageField()
    barcode = models.CharField(max_length=100)
    other = models.CharField(max_length=100)

    def __str__(self):
        return self.item_name
    
class ItemBarcode(models.Model):
    barcode = models.CharField(max_length=100, unique=True)
    item_code = models.CharField(max_length=50)
    item_name = models.CharField(max_length=100, blank=True, null=True)
    unit = models.CharField(max_length=20)
    mrp = models.DecimalField(max_digits=10, decimal_places=2)
    sale_price = models.DecimalField(max_digits=10, decimal_places=2)
    whole_price = models.DecimalField(max_digits=10, decimal_places=2)
    whole_price1 = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    generated_on = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.barcode} - {self.item_name or self.item_code}"

class Unit(models.Model):
    unit_name = models.CharField(max_length=50)
    print_name = models.CharField(max_length=50)
    decimals = models.DecimalField(max_digits=10,decimal_places=2)
    UQC = models.CharField(max_length=10)

    def __str__(self):
        return f"{self.unit_name} ({self.UQC})"
    
class Group(models.Model):
    group_name = models.CharField(max_length=50)
    alias_name = models.CharField(max_length=50)
    under = models.CharField(max_length=50)
    print_name = models.CharField(max_length=50)
    commodity = models.CharField(max_length=100)

    def __str__(self):
        return self.group_name
    
class Brand(models.Model):
    brand_name = models.CharField(max_length=50)
    alias_name = models.CharField(max_length=50)
    under = models.CharField(max_length=50)
    print_name = models.CharField(max_length=50)

    def __str__(self):
        return self.brand_name

class Tax(models.Model):
    tax_name = models.CharField(max_length=100)
    print_name = models.CharField(max_length=100)
    tax_type = models.CharField(max_length=20)  
    effect_form = models.DateField()
    rounded = models.IntegerField(default=0)   
    gst_type = models.CharField(max_length=50, blank=True, null=True)
    gst_percent = models.FloatField()
    round_type = models.CharField(max_length=20)  
    cess_percent = models.FloatField(default=0.0)

    # SGST fields
    sgst_percent = models.FloatField()
    # sales
    sgst_sales_account_1 = models.CharField(max_length=100) 
    sgst_sales_account_2 = models.CharField(max_length=100)  
    sgst_sales_return_1 = models.CharField(max_length=100)   
    sgst_sales_return_2 = models.CharField(max_length=100)   
    # purchase
    sgst_purchase_account_1 = models.CharField(max_length=100) 
    sgst_purchase_account_2 = models.CharField(max_length=100)  
    sgst_purchase_return_1 = models.CharField(max_length=100)   
    sgst_purchase_return_2 = models.CharField(max_length=100)   

    # CGST fields
    cgst_percent = models.FloatField()
    # sales
    cgst_sales_account_1 = models.CharField(max_length=100)  
    cgst_sales_account_2 = models.CharField(max_length=100)  
    cgst_sales_return_1 = models.CharField(max_length=100)   
    cgst_sales_return_2 = models.CharField(max_length=100)   
    # purchase
    cgst_purchase_account_1 = models.CharField(max_length=100)  
    cgst_purchase_account_2 = models.CharField(max_length=100)
    cgst_purchase_return_1 = models.CharField(max_length=100)   
    cgst_purchase_return_2 = models.CharField(max_length=100)   

    def __str__(self):
        return self.tax_name    
    
class Product(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
    item = models.ForeignKey(Item, on_delete=models.CASCADE)

    item_name = models.CharField(max_length=255, default="Unknown")
    code = models.CharField(max_length=100, blank=True, null=True)
    group = models.CharField(max_length=100, blank=True, null=True)
    brand = models.CharField(max_length=100, blank=True, null=True)
    unit = models.CharField(max_length=50, blank=True, null=True)
    mrp = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    whole_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    whole_rate_2 = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    sale_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
      return f"{self.item.item_name} from {self.supplier.name}"
    
class StockAdjustment(models.Model):
    ADJUSTMENT_TYPES = [
        ('add', 'Add Stock'),
        ('subtract', 'Subtract Stock'),
    ]

    REASONS = [
        ('damaged', 'Damaged'),
        ('lost', 'Lost'),
        ('expired', 'Expired'),
        ('inventory_correction', 'Inventory Correction'),
        ('manual_adjustment', 'Manual Adjustment'),
    ]

    invoice_no = models.CharField(max_length=100, default='UNKNOWN')
    batch_no = models.CharField(max_length=100, default='UNKNOWN')
    code = models.CharField(max_length=100, default='UNKNOWN')
    item_name = models.CharField(max_length=255, default='UNKNOWN')
    supplier_code = models.CharField(max_length=20, default='UNKNOWN')

    purchase_item = models.ForeignKey('MahilMartPOS_App.PurchaseItem', on_delete=models.CASCADE)
    adjustment_type = models.CharField(max_length=10, choices=ADJUSTMENT_TYPES)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.CharField(max_length=30, choices=REASONS, default='manual_adjustment')
    remarks = models.TextField(blank=True, null=True)
    adjusted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.adjustment_type.title()} {self.quantity} - {self.purchase_item}"  
    
class Payment(models.Model):
    payment_id = models.AutoField(primary_key=True)
    bill_no = models.CharField(max_length=20)
    customer = models.CharField(max_length=100) 
    date_time = models.DateTimeField(auto_now_add=True)
    cashier = models.CharField(max_length=50)  
    payment_mode = models.CharField(max_length=50)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    due_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_status = models.CharField(max_length=20)

class Expense(models.Model):
    PAYMENT_MODES = [
        ('cash', 'Cash'),
        ('bank', 'Bank'),
        ('upi', 'UPI'),
        ('cheque', 'Cheque'),
    ]

    CATEGORY_CHOICES = [
    ('Staff Salaries','Staff Salaries'),
    ('Water', 'Water Bill'),
    ('Internet', 'Internet Bill'),
    ('Electricity', 'Electricity Bill'),
    ('Rent/Lease','Rent/Lease'),
    ('Maintenance','Maintenance'),
    ('Office Supplies','Office Supplies'),
    ('Software Maintenance','Software Maintenance'),
    ('Marketing','Marketing'),
    ('Transport/Delivery','Transport/Delivery'),
    ('Miscellaneous','Miscellaneous')
]

    expenseid = models.AutoField(primary_key=True)
    datetime = models.DateTimeField()
    category = models.CharField(max_length=100, choices=CATEGORY_CHOICES)
    category_detail = models.CharField(max_length=200, blank=True, null=True)
    paid_to = models.CharField(max_length=100, blank=True, null=True)
    paymentmode = models.CharField(max_length=10, choices=PAYMENT_MODES, blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    notes = models.TextField(blank=True, null=True)
    refno = models.CharField(max_length=100, blank=True, null=True)
    reorderedby = models.CharField(max_length=100, blank=True, null=True)
    attachment = models.FileField(upload_to='expense_attachments/', blank=True, null=True)

    def __str__(self):
        return f"{self.expenseid} - {self.category} - {self.amount}"    
    
class CustomUserManager(BaseUserManager):
    def create_user(self, username, email, phone_number, role, status, password=None):
        if not email:
            raise ValueError('Email is required')
        user = self.model(
            username=username,
            email=self.normalize_email(email),
            phone_number=phone_number,
            role=role,
            status=status
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, phone_number, password=None):
        user = self.create_user(
            username=username,
            email=email,
            phone_number=phone_number,
            role='ADMIN',
            status='ACTIVE',
            password=password
        )
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user

class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = (
        ('ADMIN', 'Admin'),
        ('CASHIER', 'Cashier'),
        ('MANAGER', 'Manager'),
    )
    STATUS_CHOICES = (
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive'),
    )

    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=10, unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    can_edit_bill = models.BooleanField(default=False)
    can_print_previous_bills = models.BooleanField(default=False)
    dashboard_access = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    # Required by PermissionsMixin
    groups = models.ManyToManyField(
        Group,
        related_name='customuser_set',  # avoid conflict with auth.User
        blank=True
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name='customuser_set',  # avoid conflict with auth.User
        blank=True
    )

    objects = CustomUserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email', 'phone_number']

    def __str__(self):
        return self.username
    
class CompanyDetails(models.Model):
    company_name = models.CharField(max_length=255)
    print_name = models.CharField(max_length=255, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    pincode = models.CharField(max_length=20)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    mobile = models.CharField(max_length=20)
    email = models.EmailField()
    website = models.CharField(max_length=255, blank=True, null=True)
    gstin = models.CharField(max_length=20)
    gst_type = models.CharField(max_length=50)
    pan_no = models.CharField(max_length=20)
    fssai_no = models.CharField(max_length=20)
    trade_license_no = models.CharField(max_length=50)
    invoice_prefix = models.CharField(max_length=10)
    invoice_start_num = models.IntegerField(null=True, blank=True)
    default_tax_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    bank_name = models.CharField(max_length=255)
    account_no = models.CharField(max_length=50)
    ifsc_code = models.CharField(max_length=20)
    year_from = models.DateField(null=True, blank=True)
    year_to = models.DateField(null=True, blank=True)
    auto_backup = models.BooleanField(default=False)
    daily_backup_path = models.CharField(max_length=255, blank=True, null=True)
    printer_name = models.CharField(max_length=255, blank=True, null=True)
    auto_logout_minutes = models.IntegerField(default=0)
    password_hash = models.CharField(max_length=255)
    opening_time = models.TimeField()
    closing_time = models.TimeField()
    is_sunday_open = models.CharField(max_length=10,choices=[('Open', 'Open'), ('Closed', 'Closed')])
    admin_password = models.CharField(max_length=255, blank=True, null=True)
    confirm_password = models.CharField(max_length=255, blank=True, null=True)
    password_hash = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.company_name
       
# purchase & purchase items
class Purchase(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)   
    invoice_no = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Purchase #{self.id} - {self.supplier.name}"          

class PurchaseItem(models.Model):
    purchase = models.ForeignKey(Purchase, on_delete=models.CASCADE, related_name='items')
    item = models.ForeignKey(Item, on_delete=models.CASCADE)

    group = models.CharField(max_length=50, blank=True, null=True)
    brand = models.CharField(max_length=50, blank=True, null=True)
    unit = models.CharField(max_length=20, blank=True, null=True)
    supplier_id = models.CharField(max_length=100, blank=True, null=True)
    code = models.CharField(max_length=30, blank=True, null=True)
    item_name = models.CharField(max_length=50, blank=True, null=True)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=12, decimal_places=2)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    net_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    mrp_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    whole_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    whole_price_2 = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    sale_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    previous_qty = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_qty = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    purchased_at = models.DateField(default=timezone.now)
    batch_no = models.CharField(max_length=100, blank=True, null=True)
    expiry_date = models.DateField(blank=True, null=True)        
  
    def __str__(self):
        return f"{self.purchase.supplier.name} - {self.code} - {self.item_name}"
    
class Inventory(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    item_name = models.CharField(max_length=255)
    code = models.CharField(max_length=100)
    group = models.CharField(max_length=100, blank=True, null=True)
    brand = models.CharField(max_length=100, blank=True, null=True)
    unit = models.CharField(max_length=50)
    batch_no = models.CharField(max_length=100, blank=True, null=True)
    invoice_no = models.CharField(max_length=100, blank=True, null=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True)
    quantity = models.FloatField(default=0)
    previous_qty = models.FloatField(default=0)
    total_qty = models.FloatField(default=0)

    unit_price = models.FloatField(default=0)
    total_price = models.FloatField(default=0)
    discount = models.FloatField(default=0)
    tax = models.FloatField(default=0)
    net_price = models.FloatField(default=0)

    mrp_price = models.FloatField(default=0)
    whole_price = models.FloatField(default=0)
    whole_price_2 = models.FloatField(default=0)
    sale_price = models.FloatField(default=0)

    purchased_at = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)

    purchase = models.ForeignKey(Purchase, on_delete=models.CASCADE, null=True, blank=True)  # Optional

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.item_name} - {self.code}"        

class PurchaseBulk(models.Model):
    item_name = models.CharField(max_length=255)
    code = models.CharField(max_length=100)
    group = models.CharField(max_length=100)
    brand = models.CharField(max_length=100)
    unit = models.CharField(max_length=50)
    batch_no = models.CharField(max_length=100, null=True, blank=True)
    invoice_no = models.CharField(max_length=100, null=True, blank=True)
    quantity = models.FloatField()
    unit_price = models.FloatField()
    total_price = models.FloatField()
    discount = models.FloatField(default=0)
    tax = models.FloatField(default=0)
    net_price = models.FloatField()
    mrp_price = models.FloatField(null=True, blank=True)
    whole_price = models.FloatField(null=True, blank=True)
    whole_price_2 = models.FloatField(null=True, blank=True)
    sale_price = models.FloatField(null=True, blank=True)
    purchased_at = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    purchase_id = models.IntegerField(null=True, blank=True)
    supplier_id = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
