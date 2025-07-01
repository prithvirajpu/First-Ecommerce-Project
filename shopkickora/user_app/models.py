from datetime import date
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.models import AbstractUser
from django.utils.text import slugify
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from requests import delete





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
    country=models.CharField(max_length=100,default='India')
    is_default=models.BooleanField(default=False)
    pincode=models.CharField(max_length=6)
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
    discount_percentage = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Enter discount percentage (0-100)"
    )    
    stock = models.PositiveIntegerField(default=0)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
            original_slug = self.slug
            count = 1
            while Product.objects.filter(slug=self.slug).exists():
                self.slug = f"{original_slug}-{count}"
                count += 1
        super().save(*args, **kwargs)
        
    @property
    def discounted_price(self):
        if self.discount_percentage:
            return self.price - (self.price * self.discount_percentage / 100)
        return self.price

    @property
    def discount_percentage_effective(self):
        """Returns discount % from offers only (product or category)."""
        if self.final_price_with_offer < self.price:
            discount = ((self.price - self.final_price_with_offer) / self.price) * 100
            return round(discount)
        return 0
    @property
    def effective_discount_info(self):
        """
        Determines whether to show a badge based on best discount source.
        Returns:
            - percentage: discount % to show
            - label: 'OFF' if from offer, else None
        """
        base_price = Decimal(self.price)
        product_discount = self.discount_percentage or 0

        offer_discounts = []

        for offer in self.product_offers.all():
            if offer.is_valid():
                offer_discounts.append(offer.discount_percentage)

        if self.category:
            for offer in self.category.category_offers.all():
                if offer.is_valid():
                    offer_discounts.append(offer.discount_percentage)

        best_offer = max(offer_discounts) if offer_discounts else 0

        if best_offer > product_discount:
            return {'percentage': best_offer, 'label': 'OFF'}
        
        return {'percentage': None, 'label': None}


    @property
    def final_price_with_offer(self):
        """Price after product/category offer only (excluding direct product discount)."""
        base_price = self.price
        offer_discounts = []

        # Active Product Offers
        for offer in self.product_offers.all():
            if offer.is_valid():
                offer_discounts.append(offer.discount_percentage)

        # Active Category Offers
        if self.category:
            for offer in self.category.category_offers.all():
                if offer.is_valid():
                    offer_discounts.append(offer.discount_percentage)

        if offer_discounts:
            best_discount = max(offer_discounts)
            return round(base_price - (base_price * best_discount / 100), 2)

        return base_price


    @property
    def image_url(self):
        try:
            return self.image.url if self.image else None
        except ValueError:
            return None
    
    @property
    def final_price(self):
        """
        ✅ FINAL PRICE to be used everywhere (template/view/cart/etc).
        Chooses best among: manual discount, product offer, category offer.
        """
        base_price = Decimal(self.price)
        discounts = []

        # Add manual discount (from Product model)
        if self.discount_percentage:
            discounts.append(self.discount_percentage)

        # Add active product offers
        for offer in self.product_offers.all():
            if offer.is_valid():
                discounts.append(offer.discount_percentage)

        # Add active category offers
        if self.category:
            for offer in self.category.category_offers.all():
                if offer.is_valid():
                    discounts.append(offer.discount_percentage)

        # Apply the best (maximum) discount
        if discounts:
            best_discount = max(discounts)
            return round(base_price - (base_price * Decimal(best_discount) / 100), 2)

        # If no discounts, return original price
        return base_price




class ProductImage(models.Model):
    product=models.ForeignKey(Product,on_delete=models.CASCADE,related_name='images')
    image=models.ImageField(upload_to='product_images/')

    
    def __str__(self):
        return f"Image for {self.product.name}"


class ProductSizeStock(models.Model):
    SIZE_CHOICES = [
        ('6', '6'),
        ('7', '7'),
        ('8', '8'),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='size_stocks')
    size = models.CharField(max_length=1, choices=SIZE_CHOICES)
    quantity = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.product.name} - {self.get_size_display()} ({self.quantity})"


class Cart(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='cart_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    size = models.CharField(max_length=2)  
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product', 'size')

   
    def save(self, *args, **kwargs):
        self.size = self.size.strip()  
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user} - {self.product.name} ({self.get_size_display()})"

class Wishlist(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='wishlist_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='wishlisted_by')
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product') 
        ordering = ['-added_at']

    def __str__(self):
        return f"{self.user.username} - {self.product.name}"
    
class Order(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('SHIPPED', 'Shipped'),
        ('OUT_FOR_DELIVERY', 'Out for Delivery'),
        ('DELIVERED', 'Delivered'),
        ('CANCELLED', 'Cancelled'),
        
    ]

    PAYMENT_METHOD_CHOICES = [
        ('cod', 'Cash on Delivery'),
        ('wallet', 'Wallet'),
        ('razorpay', 'Online Payment (Razorpay)'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    address = models.ForeignKey(Address, on_delete=models.SET_NULL, null=True)
    order_id = models.CharField(max_length=20, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)

    # 🔽 Payment fields
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES,default='cod')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=255, blank=True, null=True)

    # 🔽 Optional cancel details
    cancel_reason = models.TextField(blank=True, null=True)

    # 🔽 Shipping details
    full_name = models.CharField(max_length=255)
    mobile = models.CharField(max_length=15)
    street_address = models.TextField()
    district = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=6)
    country = models.CharField(max_length=100, default='India')

    def __str__(self):
        return f"Order {self.order_id} by {self.user.email}"


class OrderItem(models.Model):
    STATUS_CHOICES = [
        ('ORDERED', 'Ordered'),
        ('CANCELLED', 'Cancelled'),
        ('RETURN_REQUESTED', 'Return Requested'),
        ('RETURN_ACCEPTED', 'Return Accepted'),
        ]
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    size = models.CharField(max_length=2)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ORDERED')  # ✅ added

    is_return_requested = models.BooleanField(default=False)
    is_return_approved = models.BooleanField(default=False)
    return_reason = models.TextField(blank=True, null=True)
    is_cancelled = models.BooleanField(default=False)
    cancel_reason = models.TextField(blank=True, null=True)
    return_requested_at = models.DateTimeField(blank=True, null=True)
    is_return_rejected = models.BooleanField(default=False)
    return_rejected_reason = models.TextField(blank=True, null=True)
    def __str__(self):
        return f"{self.product.name} (x{self.quantity})"

class Wallet(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)

    def __str__(self):
        return f"{self.user.email} - ₹{self.balance}"


class ProductOffer(models.Model):
    name = models.CharField(max_length=100, unique=True, default='default-offer')
    products = models.ManyToManyField(Product, related_name='product_offers')
    discount_percentage = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(100)])
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.discount_percentage}%)"

    def is_valid(self):
        now = timezone.now()
        return self.is_active and self.start_date <= now <= self.end_date
    
class CategoryOffer(models.Model):
    categories = models.ManyToManyField(Category, related_name='category_offers')
    discount_percentage = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(100)])
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.discount_percentage}% for {', '.join(c.name for c in self.categories.all())}"

    def is_valid(self):
        now = timezone.now()
        return self.is_active and self.start_date <= now <= self.end_date

class Wallet(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    created_at = models.DateTimeField( default=timezone.now)

    def __str__(self):
        return f"{self.user.email} - Wallet: ₹{self.balance}"

class WalletTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('CREDIT', 'Credit'),
        ('DEBIT', 'Debit'),
    ]
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=6, choices=TRANSACTION_TYPES)
    description = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
