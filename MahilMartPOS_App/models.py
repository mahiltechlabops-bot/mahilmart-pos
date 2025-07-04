from django.db import models

class Product(models.Model):
    name = models.CharField(max_length=255)
    category = models.ForeignKey('MahilMartPOS_App.Category', on_delete=models.CASCADE)
    supplier = models.ForeignKey('MahilMartPOS_App.Supplier', on_delete=models.SET_NULL, null=True, blank=True)
    stock = models.IntegerField(default=0)
    reorder_level = models.IntegerField(default=10)

    def __str__(self):
        return self.name

class Category(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

from django.db import models

class Supplier(models.Model):
    name = models.CharField(max_length=100)
    contact_person = models.CharField(max_length=100, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name
