from django.contrib import admin
from user_app.models import (CustomUser,Category,ProductImage,Product,Brand,
        Wallet,ProductSizeStock,Address,EmailChangeToken,Cart,Wishlist,Order,OrderItem
)

admin.site.register(CustomUser)
admin.site.register(Category)
admin.site.register(ProductImage)
admin.site.register(Product)
admin.site.register(Brand)
admin.site.register(ProductSizeStock)
admin.site.register(Address)
admin.site.register(EmailChangeToken)
admin.site.register(Cart)
admin.site.register(Wishlist)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(Wallet)

