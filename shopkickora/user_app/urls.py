from django.urls import path
from . import views

urlpatterns = [
   path('signup/', views.signup_view, name='signup'),
    path('verify-otp/', views.verify_otp_view, name='verify_otp'),
    path('resend-otp/', views.resend_otp, name='resend_otp'),
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    path('reset-password/<uidb64>/<token>/', views.reset_password_view, name='reset_password'),
    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('user_dashboard/', views.user_dashboard, name='user_dashboard'),
]
