from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from .models import Brand, Category, CustomUser, Product, ProductSizeStock
from user_app.forms import LoginForm
import random
import time
import re
from django.core.paginator import Paginator
from django.db.models import Q
from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse
from django.contrib.auth.tokens import PasswordResetTokenGenerator  
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode 
from django.utils.encoding import force_bytes, force_str


OTP_EXPIRY_SECONDS = 600

@never_cache
def signup_view(request):
    if request.user.is_authenticated:
        return redirect('user_dashboard')
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip().lower()  
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')

        errors = {}

        if not username:
            errors['username'] = "Username is required."
        elif not re.match(r'^(?=.*[a-zA-Z])[a-zA-Z0-9 _-]+$', username):
            errors['username'] = "Name must contain at least one letter and only use letters, numbers, spaces, hyphens, or underscores."
        elif username == "_" * len(username):
            errors['username']= "Username cannot be only underscores."
        elif CustomUser.objects.filter(username=username).exists():
            errors['username'] = "Username already taken."

        if not email:
            errors['email'] = "Email is required."
        elif not email.endswith('@gmail.com'):
            errors['email'] = 'Enter a valid Gmail address.'
        elif CustomUser.objects.filter(email=email).exists():
            errors['email'] = "Email already in use."

        if not password1:
            errors['password1'] = "Password is required."
        elif password1 != password2:
            errors['password2'] = "Passwords do not match."
        elif len(password1) < 6:
            errors['password1'] = "Password must be at least 6 characters."
        elif password1.is_digit():
            errors['password1']="Password can not contain only numbers."

        if errors:
            return render(request, 'user_app/signup.html', {'errors': errors})

        otp = random.randint(100000, 999999)
        request.session['signup_data'] = {
            'username': username,
            'email': email,
            'password': password1,
            'otp': str(otp),
            'otp_created_at': time.time()
        }

        send_mail(
            'Your ShopKickora OTP',
            f'Your OTP for ShopKickora signup is: {otp}',
            settings.EMAIL_HOST_USER,
            [email],
            fail_silently=False,
        )

        return redirect('verify_otp')

    return render(request, 'user_app/signup.html')


@never_cache
def verify_otp_view(request):
    if request.user.is_authenticated:
        return redirect('user_dashboard')
    signup_data = request.session.get('signup_data')
    if not signup_data:
        return redirect('signup')  
    if request.method == 'POST':
        entered_otp = request.POST.get('otp', '').strip()

        if len(entered_otp) != 6 or not entered_otp.isdigit():
            messages.error(request, "Enter a valid 6-digit OTP.")
            return render(request, 'user_app/verify_otp.html')

        otp_created_at = signup_data.get('otp_created_at', 0)
        if time.time() - otp_created_at > OTP_EXPIRY_SECONDS:
            messages.error(request, "OTP expired. Please resend and try again.")
            return render(request, 'user_app/verify_otp.html')

        if entered_otp == signup_data['otp']:
            user = CustomUser.objects.create_user(
                username=signup_data['username'],
                email=signup_data['email'],
                password=signup_data['password']
            )
            user.backend = 'django.contrib.auth.backends.ModelBackend'
            login(request, user)
            request.session.pop('signup_data', None)
            messages.success(request, "Account created successfully!")
            return redirect('user_dashboard')
        else:
            messages.error(request, "Invalid OTP. Please try again.")

    return render(request, 'user_app/verify_otp.html')


@never_cache
def resend_otp(request):
    signup_data = request.session.get('signup_data')
    if signup_data:
        otp = random.randint(100000, 999999)
        signup_data['otp'] = str(otp)
        signup_data['otp_created_at'] = time.time()
        request.session['signup_data'] = signup_data

        send_mail(
            'Your ShopKickora OTP (Resend)',
            f'Your new OTP is: {otp}',
            'noreply@shopkickora.com',
            [signup_data['email']],
            fail_silently=False,
        )

        messages.success(request, "A new OTP has been sent to your email.")
    else:
        messages.error(request, "Session expired or invalid. Please signup again.")
        return redirect('signup')

    return redirect('verify_otp')

@never_cache
def forgot_password_view(request):
    if request.method == "POST":
        email = request.POST.get('email', '').strip().lower()
        if not email:
            messages.error(request, "Email is required.")
            return render(request, 'user_app/forgot_password.html')

        try:
            user = CustomUser.objects.get(email=email)
            token_generator = PasswordResetTokenGenerator()
            token = token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))

            reset_url = request.build_absolute_uri(
                reverse('reset_password', kwargs={'uidb64': uid, 'token': token})
            )
            print("Password reset URL:", reset_url)

            send_mail(
                'ShopKickora Password Reset',
                f'Click the link to reset your password: {reset_url}',
                'noreply@shopkickora.com',
                [email],
                fail_silently=False,
            )

            messages.success(request, "A password reset link has been sent to your email.")
            return redirect('login')
        except CustomUser.DoesNotExist:
            messages.error(request, "No user found with this email address.")
            return render(request, 'user_app/forgot_password.html')

    return render(request, 'user_app/forgot_password.html')

@never_cache
def reset_password_view(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = CustomUser.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
        user = None

    token_generator = PasswordResetTokenGenerator()
    if user is not None and token_generator.check_token(user, token):
        if request.method == "POST":
            password1 = request.POST.get('password1', '').strip()
            password2 = request.POST.get('password2', '').strip()

            errors = {}
            if not password1:
                errors['password1'] = "Password is required."
            elif password1 != password2:
                errors['password2'] = "Passwords do not match."
            elif len(password1) < 6:
                errors['password1'] = "Password must be at least 6 characters."

            if errors:
                return render(request, 'user_app/reset_password.html', {'errors': errors, 'uidb64': uidb64, 'token': token})

            user.set_password(password1)
            user.save()
            messages.success(request, "Password reset successfully. Please log in with your new password.")
            return redirect('login')

        return render(request, 'user_app/reset_password.html', {'uidb64': uidb64, 'token': token})
    else:
        messages.error(request, "Invalid or expired reset link.")
        return redirect('forgot_password')

@never_cache
def login_view(request):
    if request.user.is_authenticated:
        return redirect('user_dashboard')
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                if user.is_blocked:
                    messages.error(request, "Your account is currently suspended.")
                    return render(request, 'user_app/login.html', {'form': form})
                elif not user.is_active:
                    messages.error(request,'Your account is inactive.')
                    return render(request, 'user_app/login.html', {'form': form})
                else:
                    login(request, user)
                    return redirect('user_dashboard')
            else:
                form.add_error(None, "Invalid username or password.")
    else:
        form = LoginForm()

    return render(request, 'user_app/login.html', {'form': form})

@never_cache
@login_required(login_url='login')
def user_dashboard(request):
    if request.user.is_superuser:
        return redirect('admin_dashboard')
    
    all_products = Product.objects.filter(is_deleted=False)
    
    best_selling_products = random.sample(list(all_products), min(4, len(all_products))) if all_products else []
    
    remaining_products = [p for p in all_products if p not in best_selling_products]
    featured_products = random.sample(list(remaining_products), min(4, len(remaining_products))) if remaining_products else []
    
    context = {
        'best_selling_products': best_selling_products,
        'featured_products': featured_products,
    }
    return render(request, 'user_app/dashboard.html', context)


@never_cache
@login_required(login_url='login')
def user_product_list(request):
    query = request.GET.get('q', '').strip()
    category = request.GET.get('category', 'all')
    sort = request.GET.get('sort', 'newest')

    brand_ids = request.GET.getlist('brand')  


    min_price_str = request.GET.get('min_price')
    max_price_str = request.GET.get('max_price')

    min_price = None
    if min_price_str:
        try:
            min_price = float(min_price_str)
        except ValueError:
            pass 

    max_price = None
    if max_price_str:
        try:
            max_price = float(max_price_str)
        except ValueError:
            pass 

    products = Product.objects.filter(
        is_deleted=False,
        category__is_deleted=False,
        category__is_active=True,
        brand__is_active=True
    )

    if category != 'all':
        products = products.filter(category__id=category)

    if brand_ids:
        products = products.filter(brand__id__in=brand_ids) 

    if query:
        products = products.filter(Q(name__icontains=query) | Q(description__icontains=query))

    if min_price is not None:
        products = products.filter(price__gte=min_price)

    if max_price is not None:
        products = products.filter(price__lte=max_price)

    if sort == 'price_low':
        products = products.order_by('price')
    elif sort == 'price_high':
        products = products.order_by('-price')
    else:
        products = products.order_by('-created_at')

    brands = Brand.objects.filter(is_active=True)
    categories = Category.objects.filter(is_active=True, is_deleted=False) 

    paginator = Paginator(products, 9)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    product_count = products.count() 

    context = {
        'page_obj': page_obj,
        'query': query,
        'category': category,
        'sort': sort,
        'product_count': product_count,
        'sizes_list': ['S', 'M', 'L'], 
        'categories': categories,
        'brands': brands,
        'selected_brands': brand_ids,
        'min_price': min_price, 
        'max_price': max_price, 
    }

    return render(request, 'user_app/user_product_list.html', context)


@never_cache
@login_required(login_url='login')
def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug)

    related_products = Product.objects.filter(category=product.category).exclude(id=product.id)[:4]

    sizes = ProductSizeStock.objects.filter(product=product, quantity__gt=0).values_list('size', flat=True)

    size_choices = dict(ProductSizeStock.SIZE_CHOICES)  
    sizes = [size for size in sizes] 

    return render(request, 'user_app/product_detail.html', {
        'product': product,
        'related_products': related_products,
        'sizes': sizes,
        'size_choices': size_choices,  
    })

@never_cache
def logout_view(request):
    logout(request)
    request.session.flush()
    list(messages.get_messages(request))
    return redirect('login')

