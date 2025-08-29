from datetime import date
from django.db import models
from django.utils import timezone
from django.utils.timezone import now
from django.core.exceptions import ValidationError
from decimal import Decimal
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager, Group, Permission, User
from django.conf import settings
from django.contrib.postgres.fields import JSONField

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
    fssai_number = models.CharField(max_length=20, blank=True, default="N/A")
    pan_number = models.CharField(max_length=20, blank=True, default="N/A")
    credit_terms = models.CharField(max_length=50, blank=True, default="N/A")
    opening_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    bank_name = models.CharField(max_length=100, blank=True, default="N/A")
    account_number = models.CharField(max_length=50, blank=True, default="N/A")
    ifsc_code = models.CharField(max_length=20, blank=True, default="N/A")
    status = models.CharField(max_length=20, default='Active')
    notes = models.TextField(blank=True, default="")    

    def __str__(self):
        return self.name        
    
class Customer(models.Model):
    name = models.CharField(max_length=100)
    cell = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    date_joined = models.DateTimeField(auto_now_add=True)
    remarks = models.TextField(blank=True, default="billing_entry")

    def __str__(self):
        return f"{self.name} ({self.cell})"     

class Billing(models.Model):
    customer = models.ForeignKey('Customer', on_delete=models.SET_NULL, null=True, blank=True)
    to = models.CharField(max_length=100, blank=True, null=True)
    bill_no = models.CharField(max_length=20, unique=True)
    date = models.DateTimeField(auto_now_add=True)
    bill_type = models.CharField(max_length=20, blank=True, null=True)  
    counter = models.CharField(max_length=50, blank=True, null=True)
    order_no = models.CharField(max_length=50, blank=True, null=True)
    sale_type = models.CharField(max_length=20, blank=True, null=True)
    received = models.DecimalField(max_digits=10, decimal_places=2)
    cash_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    card_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    balance = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    points = models.FloatField(default=0.0)  
    points_earned = models.FloatField(default=0.0)   
    status_on = models.CharField(max_length=50, default="counter_bill")
    remarks = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)    
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="bills")

    def __str__(self):
        return f"Invoice {self.bill_no}"
    
    @property
    def total_amount(self):
        return sum(item.amount for item in self.items.all())
    
    @property
    def calc_balance(self):
        """Always calculate balance dynamically"""
        return self.total_amount - (self.received or 0)
    
class BillingItem(models.Model):
    billing = models.ForeignKey(Billing, on_delete=models.CASCADE, related_name='items')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    code = models.CharField(max_length=100)
    item_name = models.CharField(max_length=255)
    unit = models.CharField(max_length=50)
    qty = models.FloatField()
    mrp = models.DecimalField(max_digits=10, decimal_places=2)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)
    amount = models.DecimalField(max_digits=10, decimal_places=2)   
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.item_name} (x{self.qty})"

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
    bill_no = models.CharField(max_length=100, null=True, blank=True)
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
    qtn_no = models.CharField(max_length=50, blank=True, null=True)

    def update_payment(self, new_payment):
        # Update paid_amount and due_balance like BillingPayment
        self.paid_amount += Decimal(new_payment)
        self.due_balance = self.total_order_amount - self.paid_amount

        # If fully paid, mark completed
        if self.due_balance <= 0:
            self.order_status = 'completed'
        self.save()

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
    qtn_no = models.CharField(max_length=20, unique=True)
    date = models.DateField(auto_now_add=True)
    name = models.CharField(max_length=100)
    cell = models.CharField(max_length=15)
    email = models.EmailField()
    address = models.TextField(blank=True, null=True)
    date_joined = models.DateField()
    sale_type = models.CharField(max_length=50)
    bill_type = models.CharField(max_length=50)
    counter = models.CharField(max_length=50)
    points = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    points_earned = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    items = models.JSONField()
    bill_no = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return f"Quotation #{self.qtn_no} - {self.name}"
    
    def __str__(self):
        return f"Quotation #{self.qtn_no} - {self.name}"

class BillingPayment(models.Model):
    billing = models.ForeignKey(Billing, on_delete=models.CASCADE, related_name="payments")
    bill_no = models.CharField(max_length=50, blank=True)  
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    already_paid = models.DecimalField(max_digits=10, decimal_places=2)
    new_payment = models.DecimalField(max_digits=10, decimal_places=2)
    balance = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(default=timezone.now)
    payment_mode = models.CharField(max_length=50, choices=(('Cash','Cash'),('Card','Card'),('Online','Online')), default='Cash')

    def save(self, *args, **kwargs):
        if not self.bill_no:
            self.bill_no = self.billing.bill_no  
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Payment {self.id} for {self.bill_no}"
    
class BillType(models.Model):
    billtype_id = models.IntegerField(unique=True)
    billtype = models.CharField(max_length=100)

    def __str__(self):
        return self.billtype
    
class PaymentMode(models.Model):
    mode_id = models.IntegerField(unique=True)
    mode_name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.mode_name
    
class Counter(models.Model):
    counter_id = models.IntegerField(unique=True)
    counter_name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.counter_name    

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    item_name = models.CharField(max_length=100)
    quantity = models.PositiveIntegerField()
    rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    amount = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return self.item_name       

class SaleReturn(models.Model):
    billing = models.ForeignKey(Billing, on_delete=models.CASCADE)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    return_reason = models.TextField()
    total_return_qty = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_refund_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

class SaleReturnItem(models.Model):
    sale_return = models.ForeignKey(SaleReturn, on_delete=models.CASCADE)
    billing_item = models.ForeignKey(BillingItem, on_delete=models.SET_NULL, null=True)
    code = models.CharField(max_length=100)
    item_name = models.CharField(max_length=255)
    unit = models.CharField(max_length=100)
    qty = models.DecimalField(max_digits=10, decimal_places=2)
    mrp = models.DecimalField(max_digits=10, decimal_places=2)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    return_qty = models.DecimalField(max_digits=10, decimal_places=2)
    return_amount = models.DecimalField(max_digits=10, decimal_places=2)       
    
class Item(models.Model):  
    code = models.CharField(max_length=100, unique=True)
    item_name = models.CharField(max_length=50)
    print_name = models.CharField(max_length=50, blank=True, null=True)    
    status = models.CharField(max_length=10)
    unit = models.CharField(max_length=20, blank=True, null=True)
    P_unit = models.CharField(max_length=20, blank=True, null=True)
    group = models.CharField(max_length=100, blank=True, null=True)
    brand = models.CharField(max_length=100, blank=True, null=True)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    HSN_SAC = models.BigIntegerField(blank=True, null=True, default=0)
    P_rate = models.FloatField()
    cost_rate = models.FloatField()
    MRSP = models.FloatField()
    sale_rate = models.FloatField()
    whole_rate = models.FloatField()
    whole_rate_2 = models.FloatField()
    use_MRP = models.CharField(max_length=10)
    min_stock = models.CharField(max_length=100)
    stock_item = models.CharField(max_length=10)
    carry_over = models.CharField(max_length=10)
    manual = models.CharField(max_length=10)
    points = models.BigIntegerField()
    cess_per_qty =  models.BigIntegerField()
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
    decimals = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
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

    purchase = models.ForeignKey('Purchase', on_delete=models.CASCADE, null=True, blank=True)
    invoice_no = models.CharField(max_length=100, blank=True, null=True)
    batch_no = models.CharField(max_length=100, default='UNKNOWN')
    code = models.CharField(max_length=100, default='UNKNOWN')
    item_name = models.CharField(max_length=255, default='UNKNOWN')
    unit = models.CharField(max_length=100, blank=True, null=True)
    supplier_code = models.CharField(max_length=20, default='UNKNOWN')
    purchase_item = models.ForeignKey('MahilMartPOS_App.PurchaseItem', on_delete=models.CASCADE)
    adjustment_type = models.CharField(max_length=10, choices=ADJUSTMENT_TYPES)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)  
    split_unit = models.DecimalField(max_digits=10, decimal_places=2, default=0)   
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00')) 
    cost_price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    adjusted_net_price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    reason = models.CharField(max_length=30, choices=REASONS, default='manual_adjustment')
    remarks = models.TextField(blank=True, null=True)
    adjusted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.adjustment_type.title()} {self.quantity} - {self.purchase_item}"  
    

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
    total_products = models.FloatField(default=0)
    total_amount = models.FloatField(default=0)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    outstanding_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    payment_mode = models.CharField(
        max_length=50,
        choices=[
            ('Cash', 'Cash'),
            ('Card', 'Card'),
            ('Bank Transfer', 'Bank Transfer'),
            ('UPI', 'UPI'),
            ('Cheque', 'Cheque'),
            ('Credit', 'Credit'),
            ('Partial Credit', 'Partial Credit'),
        ],
        blank=True,
        null=True
    )
    payment_rate = models.DecimalField(max_digits=7, decimal_places=2, default=0.00)  
    payment_reference = models.CharField(max_length=255, blank=True, null=True)
    bill_attachment = models.FileField(upload_to='bill_attachments/', blank=True, null=True) 

    def save(self, *args, **kwargs):
        if self.total_amount and self.amount_paid is not None:
            self.outstanding_amount = max(self.total_amount - self.amount_paid, 0)
            self.payment_rate = (
                (self.amount_paid / self.total_amount) * 100
                if self.total_amount > 0 else 0
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Purchase #{self.id} - {self.supplier.name}"         

class PurchaseItem(models.Model):
    purchase = models.ForeignKey(Purchase, on_delete=models.CASCADE, related_name='items')
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    hsn = models.CharField(max_length=50, blank=True, null=True)
    group = models.CharField(max_length=50, blank=True, null=True)
    brand = models.CharField(max_length=50, blank=True, null=True)
    unit = models.CharField(max_length=20, blank=True, null=True)
    supplier_id = models.CharField(max_length=100, blank=True, null=True)
    code = models.CharField(max_length=30, blank=True, null=True)
    item_name = models.CharField(max_length=50, blank=True, null=True)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_qty = models.DecimalField(max_digits=10, decimal_places=2, default=0) #unit quantity
    split_unit = models.DecimalField(max_digits=10, decimal_places=2, default=0) #kg/ltr/pcs
    split_unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0) #kg/ltr/pcs price
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=12, decimal_places=2)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    taxable_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    net_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    cost_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    mrp_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    whole_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    whole_price_2 = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    sale_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    previous_qty = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_qty = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    purchased_at = models.DateField(default=timezone.now)
    batch_no = models.CharField(max_length=100, blank=True, null=True)
    expiry_date = models.DateField(blank=True, null=True) 
    status = models.CharField(max_length=20, default="in_stock")       
  
    def __str__(self):
        return f"{self.purchase.supplier.name} - {self.code} - {self.item_name}"
    
class PurchasePayment(models.Model):
    purchase = models.ForeignKey(Purchase, on_delete=models.CASCADE, related_name="payments")
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name="payments",default=1)
    invoice_no = models.CharField(max_length=100, blank=True, null=True)
    payment_date = models.DateField(default=now)
    payment_amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_mode = models.CharField(max_length=50, blank=True, null=True)
    payment_reference = models.CharField(max_length=100, blank=True, null=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    balance_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    @property
    def payment_status(self):
        if self.purchase.outstanding_amount <= 0:
            return "Completed"
        elif self.purchase.amount_paid == 0:
            return "Unpaid"
        else:
            return "Partial"

    def __str__(self):
        return f"Payment {self.id} for Invoice {self.purchase.invoice_no}"
    
class PurchaseTracking(models.Model):
    purchase = models.ForeignKey(Purchase, on_delete=models.CASCADE, related_name="tracking")
    item = models.ForeignKey(Item, on_delete=models.SET_NULL, null=True, blank=True)

    # PurchaseItem snapshot fields
    existing_quantity = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)  
    updated_quantity = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)    
    total_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)   
    whole_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    whole_price_2 = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    sale_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    discount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    net_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    tax = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True)   
    expiry_date = models.DateField(null=True, blank=True)
    purchased_at = models.DateTimeField(null=True, blank=True)

    code = models.CharField(max_length=100, null=True, blank=True)
    item_name = models.CharField(max_length=255, null=True, blank=True)    
    hsn = models.CharField(max_length=50, null=True, blank=True)

    split_unit = models.CharField(max_length=50, null=True, blank=True)
    split_unit_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    unit_qty = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    status = models.CharField(max_length=50, null=True, blank=True)
    cost_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    taxable_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    # Meta
    tracked_at = models.DateTimeField(auto_now_add=True)   
    
class Inventory(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    item_name = models.CharField(max_length=255)
    code = models.CharField(max_length=100)
    hsn = models.CharField(max_length=20, blank=True, null=True)
    group = models.CharField(max_length=100, blank=True, null=True)
    brand = models.CharField(max_length=100, blank=True, null=True)
    unit = models.CharField(max_length=50)
    batch_no = models.CharField(max_length=100, blank=True, null=True)   
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True)
    quantity = models.FloatField(default=0)
    unit_qty = models.FloatField(default=0) #unit quantity
    split_unit = models.FloatField(default=0) #kg/ltr/pcs
    split_unit_price = models.FloatField(default=0) #kg/ltr/pcs price
    previous_qty = models.FloatField(default=0)
    total_qty = models.FloatField(default=0)
    unit_price = models.FloatField(default=0)
    total_price = models.FloatField(default=0)
    discount = models.FloatField(default=0)
    taxable_price = models.FloatField(default=0)
    tax = models.FloatField(default=0)
    cost_price = models.FloatField(default=0)
    net_price = models.FloatField(default=0)
    mrp_price = models.FloatField(default=0)
    whole_price = models.FloatField(default=0)
    whole_price_2 = models.FloatField(default=0)
    sale_price = models.FloatField(default=0)
    purchased_at = models.DateTimeField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    purchase = models.ForeignKey(Purchase, on_delete=models.CASCADE, null=True, blank=True)  # Optional
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default="in_stock")

    def __str__(self):
        return f"{self.item_name} - {self.code}"        
