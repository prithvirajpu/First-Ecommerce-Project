from django.contrib import admin
from user_app.models import CustomUser,Category,ProductImage,Product,Brand,ProductSizeStock

# Register your models here.

admin.site.register(CustomUser)
admin.site.register(Category)
admin.site.register(ProductImage)
admin.site.register(Product)
admin.site.register(Brand)
admin.site.register(ProductSizeStock)
