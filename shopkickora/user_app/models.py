from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractUser
# Create your models here.

class CustomUser(AbstractUser):
    is_blocked=models.BooleanField(default=False)

    def __str__(self):
        return self.username

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    
class Brand(models.Model):
    name=models.CharField(max_length=100,unique=True)
    description=models.TextField(blank=True)
    logo=models.ImageField(upload_to='brand_logos/',blank=True,null=True)
    status=models.CharField(max_length=20,default='active')
    created_at=models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    
class Product(models.Model):
    name=models.CharField(max_length=200)
    description=models.TextField(blank=True)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    price=models.DecimalField(max_digits=10,decimal_places=2)
    stock=models.IntegerField()
    category=models.ForeignKey(Category,on_delete=models.SET_NULL,null=True)
    brand=models.ForeignKey(Brand,on_delete=models.CASCADE,null=True,blank=True)
    is_deleted=models.BooleanField(default=False)
    created_at=models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.name
    
class ProductImage(models.Model):
    product=models.ForeignKey(Product,on_delete=models.CASCADE,related_name='images')
    image=models.ImageField(upload_to='product_images/')

    def __str__(self):
        return f"Image for {self.product.name}"
