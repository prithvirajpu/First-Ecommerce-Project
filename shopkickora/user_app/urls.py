from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('verify-otp/', views.verify_otp_view, name='verify_otp'),
    path('resend-otp/', views.resend_otp, name='resend_otp'),
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),  
    path('reset-password/<uidb64>/<token>/', views.reset_password_view, name='reset_password'),
    path('logout/', views.logout_view, name='logout'),
    path('user_dashboard/', views.user_dashboard, name='user_dashboard'),
    path('user_product_list/', views.user_product_list, name='user_product_list'),
    path('product/<slug:slug>/', views.product_detail, name='product_detail'),


    path('password-reset/',
         auth_views.PasswordResetView.as_view(
             template_name='user_app/forgot_password.html',
             email_template_name='user_app/password_reset_email.html',
             success_url='/verify-otp/'
         ), 
         name='password_reset'),

    path('profile/',views.user_profile,name='user_profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('change-password/', views.change_password, name='change_password'),
    path('remove-profile-image/', views.remove_profile_image, name='remove_profile_image'),
    path('address/', views.address_view, name='address_view'),
    path('address/add/', views.add_address, name='add_address'),
    path('address/edit/<int:address_id>/', views.edit_address, name='edit_address'),
    path('address/delete/<int:address_id>/', views.delete_address, name='delete_address'),
    path('cart/', views.cart_view, name='cart_view'),
    path('add-to-cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/increment/<int:item_id>/', views.increment_quantity, name='increment_quantity'),
    path('cart/decrement/<int:item_id>/', views.decrement_quantity, name='decrement_quantity'),
    path('cart/remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('wishlist/', views.wishlist_view, name='wishlist_view'),
    path('wishlist/toggle/<int:product_id>/', views.toggle_wishlist, name='toggle_wishlist'),
    path('checkout/', views.checkout, name='checkout'),
    path('place-order/', views.place_order, name='place_order'),
    path('orders/<int:order_id>/', views.user_order_detail, name='user_order_detail'),
    path('order-success/<int:order_id>/', views.order_success, name='order_success'),
    path('my-orders/', views.user_order_list, name='user_order_list'),
    path('validate-cart-stock/', views.validate_cart_stock, name='validate_cart_stock'),
    path('order/<int:order_id>/cancel/', views.cancel_order, name='cancel_order'),
    path('order/item/<int:item_id>/return/', views.request_return, name='request_return'),
    path('order/<int:order_id>/invoice/', views.download_invoice, name='download_invoice'),
    path('wallet_page/',views.wallet_page,name='wallet_page'),
    path('payment-success/', views.payment_success, name='payment_success'),
    path('payment-failed/', views.payment_failed, name='payment_failed'),
    path('apply-coupon/', views.apply_coupon, name='apply_coupon'),
    # path('remove-coupon/', views.remove_coupon, name='remove_coupon'),


]
