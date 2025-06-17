from django.conf import settings
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractUser
from django.utils.text import slugify
from django.db import models
from django.contrib.auth import get_user_model





class EmailChangeToken(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    new_email = models.EmailField()
    token = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} -{self.new_email}"
class CustomUser(AbstractUser):
    is_email_verified = models.BooleanField(default=True)
    is_blocked=models.BooleanField(default=False)
    profile_image=models.ImageField(upload_to='profiles/',default='profiles/default.png',null=True,blank=True)
    otp_code=models.CharField(max_length=6,blank=True,null=True)
    otp_created_at=models.DateTimeField(blank=True,null=True)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()
    def __str__(self):
        return self.username

class Address(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='addresses')
    full_name=models.CharField(max_length=255)
    district=models.CharField(max_length=100)
    state=models.CharField(max_length=100)
    country=models.CharField(max_length=100)
    is_default=models.BooleanField(default=False)
    pincode=models.IntegerField()
    street_address=models.TextField()
    email=models.EmailField()
    mobile=models.CharField(max_length=15)

    def __str__(self):
        return f"{self.full_name}, {self.street_address}, {self.district}, {self.pincode}"

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)  
    def __str__(self):
        return self.name
    
class Brand(models.Model):
    name=models.CharField(max_length=100,unique=True)
    description=models.TextField(blank=True)
    logo=models.ImageField(upload_to='brand_logos/',blank=True,null=True)
    created_at=models.DateTimeField(auto_now_add=True)
    is_active=models.BooleanField(default=True)
    status = models.BooleanField(default=True)

    def __str__(self):
        return self.name
    
    
class Product(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True, null=True)  
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField()
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
            original_slug = self.slug
            count = 1
            while Product.objects.filter(slug=self.slug).exists():
                self.slug = f"{original_slug}-{count}"
                count += 1
        super().save(*args, **kwargs)
        
    def __str__(self):
        return self.name

    @property
    def image_url(self):
        try:
            return self.image.url if self.image else None
        except ValueError:
            return None
    
class ProductImage(models.Model):
    product=models.ForeignKey(Product,on_delete=models.CASCADE,related_name='images')
    image=models.ImageField(upload_to='product_images/')

    
    def __str__(self):
        return f"Image for {self.product.name}"



class ProductSizeStock(models.Model):
    SIZE_CHOICES = [
        ('S', 'Small'),
        ('M', 'Medium'),
        ('L', 'Large'),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='size_stocks')
    size = models.CharField(max_length=1, choices=SIZE_CHOICES)
    quantity = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.product.name} - {self.get_size_display()} ({self.quantity})"


class Cart(models.Model):
    SIZE_CHOICES = [
        ('S', 'Small'),
        ('M', 'Medium'),
        ('L', 'Large'),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='cart_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    size = models.CharField(max_length=1, choices=SIZE_CHOICES)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product', 'size')  # one cart item per product per size

    @property
    def get_size_display(self):
        return dict(ProductSizeStock.SIZE_CHOICES).get(self.size, self.size)

    def __str__(self):
        return f"{self.user} - {self.product.name} ({self.get_size_display()})"

class Wishlist(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='wishlist_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='wishlisted_by')
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product')  # Prevent duplicates
        ordering = ['-added_at']

    def __str__(self):
        return f"{self.user.username} - {self.product.name}"