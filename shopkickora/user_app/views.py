from django.shortcuts import render,redirect
from django.contrib.auth import login,authenticate
from django.contrib import messages
from user_app.forms import UserSignupForm
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required


def signup_view(request):
    if request.method=='POST':
        form=UserSignupForm(request.POST)
        if form.is_valid():
            user=form.save()
            login(request,user)
            messages.success(request,'Account created successfully')
            return redirect('user_dashboard')
    else:
        form=UserSignupForm()
    return render(request,'user_app/signup.html',{'form':form})

def login_view(request):
    if request.user.is_authenticated and request.user.is_superuser :
        return redirect('admin_dashboard')
    if request.method=="POST":
        form=AuthenticationForm(request,data=request.POST)
        if form.is_valid():
            user=form.get_user()
            login(request,user)
            return redirect('user_dashboard')
        else:
            messages.error(request,'Invalid username or password')
    else:
        form=AuthenticationForm()
    return render(request,'user_app/login.html',{'form':form})
    
def logout_view(request):
    logout(request)
    request.session.flush()
    return redirect('login')

@login_required(login_url='login')
def user_dashboard(request):
    return render(request,'user_app/dashboard.html')
