from django.contrib import admin
from .models import CustomUser,Category,ProductImage,Product,Brand

# Register your models here.

admin.site.register(CustomUser)
admin.site.register(Category)
admin.site.register(ProductImage)
admin.site.register(Product)
admin.site.register(Brand)