from django.shortcuts import render,redirect
from django.contrib.auth import login,authenticate
from django.contrib import messages
from user_app.forms import LoginForm
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
import re
from .models import CustomUser

@never_cache
def signup_view(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')

        errors = {}

        if not username:
            errors['username'] = "Username is required."
        elif CustomUser.objects.filter(username=username).exists():
            errors['username'] = "Username already taken."

        if not email:
            errors['email'] = "Email is required."
        elif not email.endswith('@gmail.com'):
            errors['email']='Enter a valid email id'
        elif CustomUser.objects.filter(email=email).exists():
            errors['email'] = "Email already in use."

        if not password1:
            errors['password1'] = "Password is required."
        elif password1 != password2:
            errors['password2'] = "Passwords do not match."
        elif len(password1) < 6:
            errors['password1'] = "Password must be at least 6 characters."
        if errors:
            return render(request, 'user_app/signup.html', {'errors': errors})
        user = CustomUser.objects.create_user(username=username, email=email, password=password1)
        user.save()
        login(request, user)
        messages.success(request, "Account created successfully!")
        return redirect('user_dashboard')
    return render(request, 'user_app/signup.html')

@never_cache
def login_view(request):
    if request.user.is_authenticated:
        return redirect('user_dashboard')
    if request.method=="POST":
        form=LoginForm(request.POST)
        if form.is_valid():
            username=form.cleaned_data.get('username')
            password=form.cleaned_data.get('password')
            user=authenticate(request,username=username,password=password)
            if user is not None:
                if user.is_blocked:
                    messages.error(request,"Your Account currently suspended..")
                else:
                    login(request,user)
                    return redirect('user_dashboard')
            else:
                form.add_error(None, "Invalid username or password.")        
    else:
        form=LoginForm()
    return render(request,'user_app/login.html',{'form':form})
    
@never_cache
@login_required(login_url='login')
def user_dashboard(request):
    if request.user.is_superuser:
        return redirect('admin_dashboard') 
    return render(request,'user_app/dashboard.html')


def logout_view(request):
    logout(request)
    request.session.flush()
    return redirect('login')


