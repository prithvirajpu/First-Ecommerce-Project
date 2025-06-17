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
    # urls.py
    path('verify-email-change/<str:token>/', views.verify_email_change, name='verify_email_change'),
    path('change-password/', views.change_password, name='change_password'),
    path('remove-profile-image/', views.remove_profile_image, name='remove_profile_image'),
    path('address/', views.address_view, name='address_view'),
    path('address/add/', views.add_address, name='add_address'),
    path('address/edit/<int:address_id>/', views.edit_address, name='edit_address'),
    path('address/delete/<int:address_id>/', views.delete_address, name='delete_address'),
    path('cart/', views.cart_view, name='user_cart'),


]
