from datetime import datetime
from django import forms
from .models import Supplier
from .models import CompanyDetails
from .models import Billing,Order,OrderItem,Expense
from django.forms.widgets import DateTimeInput
from django.forms.widgets import DateInput
import re

class BillingForm(forms.ModelForm):
    class Meta:
        model = Billing
        fields = '__all__'
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }  

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and not re.match(r'^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$', email, re.IGNORECASE):
            raise forms.ValidationError("Please enter a valid email address.")
        return email  

class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = '__all__'

        widgets = {
            'customer_name': forms.TextInput(attrs={'placeholder': 'Enter customer name'}),
            'phone_number': forms.TextInput(attrs={'placeholder': 'Enter phone number'}),
            'address': forms.Textarea(attrs={'rows': 1, 'placeholder': 'Enter address'}),
            'email': forms.EmailInput(attrs={'placeholder': 'Enter email'}),
            'date_of_order': DateTimeInput(attrs={'type': 'datetime-local','readonly': 'readonly',},format='%Y-%m-%dT%H:%M'),
            'expected_delivery_datetime': DateTimeInput(attrs={'type': 'datetime-local'},format='%Y-%m-%dT%H:%M'),
            'delivery': forms.Select(choices=Order.DELIVERY_CHOICES),
            'charges': forms.NumberInput(attrs={'placeholder': 'Delivery charges'}),     
            'total_order_amount': forms.NumberInput(attrs={'readonly': 'readonly'}),
            'advance': forms.NumberInput(attrs={'placeholder': 'Advance paid'}),        
            'due_balance': forms.NumberInput(attrs={'readonly': 'readonly'}),
            'full_amount_paid': forms.CheckboxInput(attrs={'disabled': True}),
            'payment_type': forms.Select(choices=Order.PAYMENT_TYPE_CHOICES),
            'order_status': forms.Select(choices=Order.ORDER_STATUS_CHOICES),
        }
        
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            
            if not self.is_bound:
                self.fields['date_of_order'].initial = datetime.now().strftime('%Y-%m-%dT%H:%M')
                self.fields['customer_name'].required = True
                self.fields['address'].required = True
                self.fields['email'].required = True

class OrderItemForm(forms.ModelForm):
    class Meta:
        model = OrderItem
        fields = ['item_name', 'quantity', 'rate', 'amount']


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = '__all__'
        widgets = {
            'datetime': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'readonly': 'readonly'
            }),
            'notes': forms.Textarea(attrs={'rows': 1}),
            'date': DateInput(attrs={'type': 'date'}),
        }

class PaymentForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['total_order_amount','advance', 'due_balance']
                    

class SupplierForm(forms.ModelForm):
    phone = forms.RegexField(
            regex=r'^[6-9]\d{9}$',
            error_messages={
                'invalid': "Enter a valid 10-digit phone number starting with 6, 7, 8, or 9."
            },
            widget=forms.TextInput(attrs={'class': 'form-control'})
        )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Supplier
        fields = ['name', 'contact_person', 'phone', 'email', 'address']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class CompanySettingsForm(forms.ModelForm):

    invoice_start_number = forms.IntegerField(
    widget=forms.NumberInput(attrs={'class': 'form-control'}),
    required=False
)

    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=False,
        label='Confirm Password'
    )

    class Meta:
        model = CompanyDetails
        fields = '__all__'
        widgets = {
            'admin_password': forms.PasswordInput(attrs={'class': 'form-control'}),
            'auto_backup': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'exit_backup_path': forms.TextInput(attrs={'class': 'form-control'}),
            'daily_backup_path': forms.TextInput(attrs={'class': 'form-control'}),
            'printer_name': forms.TextInput(attrs={'class': 'form-control'}),
            'auto_logout_minutes': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    data_path = forms.CharField(required=False)    
    company_name = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    print_name = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    address = forms.CharField(widget=forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}))
    pincode = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    state = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    country = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    phone = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    mobile = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control'}))
    website = forms.URLField(widget=forms.URLInput(attrs={'class': 'form-control'}))

    gstin = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    gst_type = forms.ChoiceField(choices=[('Regular', 'Regular'), ('Composition', 'Composition')], widget=forms.Select(attrs={'class': 'form-control'}))
    pan_no = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    tin_no = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    cst_no = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    fssai_no = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    trade_license_no = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))

    
    invoice_prefix = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    invoice_start_num = forms.IntegerField(
    required=False,
    widget=forms.NumberInput(attrs={'class': 'form-control'})
)

    default_tax_rate = forms.DecimalField(widget=forms.NumberInput(attrs={'class': 'form-control'}))

    bank_name = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    account_no = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    ifsc_code = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    upi_id = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))

    auto_backup = forms.BooleanField(required=False, widget=forms.CheckboxInput())
    daily_backup_path = forms.CharField(required=False)
    auto_logout_minutes = forms.IntegerField(widget=forms.NumberInput(attrs={'class': 'form-control'}))
    admin_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    force_password_change = forms.BooleanField(required=False, widget=forms.CheckboxInput())

    opening_time = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}))
    closing_time = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}))
 
    account_code = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    barcode_prefix = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    support_contact = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    social_links = forms.URLField(widget=forms.URLInput(attrs={'class': 'form-control'}))

    year_from = forms.DateField(widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}), required=False)
    year_to = forms.DateField(widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}), required=False)
    invoice_start_number = forms.IntegerField(
    required=False,
    widget=forms.NumberInput(attrs={'class': 'form-control'})
)
    
    printer_name = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}), required=False)
    password_hash = forms.CharField(required=False)
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('admin_password')
        confirm = cleaned_data.get('confirm_password')

        if password and confirm and password != confirm:
            raise forms.ValidationError("Passwords do not match.")

        return cleaned_data

class ItemForm(forms.Form):
    code = forms.CharField(label="Code", required=True)
    status = forms.ChoiceField(label="Status Active", choices=[("Yes", "Yes"), ("No", "No")], initial="No")
    item_name = forms.CharField(label="Item Name", required=True)
    print_name = forms.CharField(label="Print Name", required=False)
    unit = forms.CharField(label="Unit", required=False)
    p_unit = forms.CharField(label="P. Unit", required=False)
    group = forms.CharField(label="Group", required=False)
    brand = forms.CharField(label="Brand", required=False)
    tax = forms.CharField(label="Tax", required=False)
    hsn_sac = forms.CharField(label="HSN / SAC", required=False)
    use_mrp = forms.ChoiceField(label="Use MRP", choices=[("Yes", "Yes"), ("No", "No")], initial="No")
    points = forms.CharField(label="Points", required=False)
    cess_per_qty = forms.CharField(label="Cess Per Qty", required=False)

    # Pricing Section
    p_rate = forms.CharField(label="P. Rate", required=False)
    cost_rate = forms.CharField(label="Cost Rate", required=False)
    mrp = forms.CharField(label="MRP", required=False)
    sale_rate = forms.CharField(label="Sale Rate", required=False)
    whole_rate = forms.CharField(label="Whole Rate", required=False)
    whole_rate2 = forms.CharField(label="Whole Rate 2", required=False)
    min_stock = forms.CharField(label="Min Stock", required=False)

    # Options
    carry_over = forms.ChoiceField(label="Carry Over", choices=[("Yes", "Yes"), ("No", "No")], initial="No")
    manual = forms.ChoiceField(label="Manual", choices=[("Yes", "Yes"), ("No", "No")], initial="No")
    stock_item = forms.ChoiceField(label="Stock Item", choices=[("Yes", "Yes"), ("No", "No")], initial="No")