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

    path('password-reset/',
         auth_views.PasswordResetView.as_view(
             template_name='user_app/forgot_password.html',
             email_template_name='user_app/password_reset_email.html',
             success_url='/verify-otp/'
         ), 
         name='password_reset'),
]
