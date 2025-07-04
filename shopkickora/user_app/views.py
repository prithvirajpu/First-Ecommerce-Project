import random
import re
import time
import json
import razorpay

from django.template.loader import get_template
from xhtml2pdf import pisa
from django.db import transaction
from django.http import JsonResponse,HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.core.exceptions import ValidationError
from django.core.signing import TimestampSigner
from django.core.validators import validate_email
from django.utils.crypto import get_random_string
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils import timezone

from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required,user_passes_test
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.messages import get_messages


from django.views.decorators.cache import never_cache

from django.core.paginator import Paginator
from decimal import Decimal
from .models import (
    Brand, Category, Coupon, CustomUser, Product,
    ProductSizeStock, Address, WalletTransaction,Wishlist,Cart,
    Order,OrderItem,Cart,Wallet,
)

from user_app.forms import LoginForm, ProfileImageForm 
from django.conf import settings
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils.crypto import get_random_string




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
        elif password1.isdigit():
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
    storage = get_messages(request)
    for _ in storage:
        pass
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                if user.is_blocked:
                    messages.error(request, "Your account is currently suspended.")
                    return redirect('login')
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
    if request.user.is_blocked:
        logout(request)
        return redirect('login')
    
    all_products = Product.objects.filter(is_deleted=False)
    
    best_selling_products = random.sample(list(all_products), min(4, len(all_products))) if all_products else []
    
    remaining_products = [p for p in all_products if p not in best_selling_products]
    featured_products = random.sample(list(remaining_products), min(4, len(remaining_products))) if remaining_products else []

    wishlist_products = []
    if request.user.is_authenticated:
        wishlist_products = Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True)

    context = {
        'best_selling_products': best_selling_products,
        'featured_products': featured_products,
        'wishlist_products': list(wishlist_products),  
    }
    return render(request, 'user_app/dashboard.html', context)


@never_cache
@login_required(login_url='login')
def user_product_list(request):
    query = request.GET.get('q', '').strip()
    category = request.GET.get('category', 'all')
    sort = request.GET.get('sort', 'newest')
    brand_ids = request.GET.getlist('brand')
    selected_size = request.GET.get('size')

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
        products = products.filter(name__icontains=query)

    if min_price is not None:
        products = products.filter(price__gte=min_price)

    if max_price is not None:
        products = products.filter(price__lte=max_price)

    if selected_size:
        products = products.filter(
        size_stocks__size=selected_size,
        size_stocks__quantity__gt=0
    )

    if sort == 'price_low':
        products = products.order_by('price')
    elif sort == 'price_high':
        products = products.order_by('-price')
    else:
        products = products.order_by('-created_at')

    brands = Brand.objects.filter(is_active=True)
    categories = Category.objects.filter(is_active=True, is_deleted=False)

    paginator = Paginator(products.distinct(), 9)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    product_count = products.count()

    context = {
        'page_obj': page_obj,
        'query': query,
        'category': category,
        'sort': sort,
        'product_count': product_count,
        'sizes_list': ['6', '7', '8'],  # ✅ This replaces the need for 'split'
        'selected_size': selected_size,  # ✅ Keep track of current selection
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

    # Get related products from the same category
    related_products = Product.objects.filter(
        category=product.category
    ).exclude(id=product.id)[:4]

    # Get available sizes (with stock > 0)
    sizes = ProductSizeStock.objects.filter(
        product=product, quantity__gt=0
    ).values_list('size', flat=True).distinct()

    # Optional: If you still want a label (though '6' is already display-friendly)
    size_choices = dict(ProductSizeStock.SIZE_CHOICES)

    return render(request, 'user_app/product_detail.html', {
        'product': product,
        'related_products': related_products,
        'sizes': sizes,
        'size_choices': size_choices,
    })



@login_required
def wishlist_view(request):
    wishlist_items = Wishlist.objects.filter(user=request.user).select_related('product')
    return render(request, 'user_app/wishlist.html', {'wishlist_items': wishlist_items})


@require_POST
@login_required
def toggle_wishlist(request,product_id):
    if not product_id:
        return JsonResponse({'status': 'error', 'message': 'Product ID required'}, status=400)

    try:
        product = Product.objects.get(id=product_id, is_deleted=False)
        wishlist_item, created = Wishlist.objects.get_or_create(user=request.user, product=product)

        if not created:
            wishlist_item.delete()
            return JsonResponse({'status': 'removed'})
        else:
            return JsonResponse({'status': 'added'})
    except Product.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Product not found'}, status=404)

def get_cart_grand_total(user):
    cart_items = Cart.objects.filter(user=user).select_related('product')
    grand_total = Decimal('0.00')

    for item in cart_items:
        final_price = item.product.final_price
        grand_total += final_price * item.quantity

    return grand_total

@login_required
def cart_view(request):
    cart_items = Cart.objects.filter(user=request.user).select_related('product')
    grand_total = Decimal('0.00')
    original_total = Decimal('0.00')
    total_discount = Decimal('0.00')  # manual discount
    total_offer = Decimal('0.00')     # offer discount
    stock_info = {}

    for item in cart_items:
        try:
            stock = ProductSizeStock.objects.get(product=item.product, size=item.size)
            item.max_quantity = stock.quantity
            stock_info[item.id] = stock.quantity
        except ProductSizeStock.DoesNotExist:
            item.max_quantity = 0
            stock_info[item.id] = 0

        original_price = item.product.price
        manual_discounted_price = item.product.discounted_price  # price after manual discount
        final_price = item.product.final_price  # best (lowest) price after all discounts

        # For display
        item.discounted_price = final_price
        item.total_price = final_price * item.quantity

        original_total += original_price * item.quantity
        grand_total += final_price * item.quantity

        # Detect source of discount
        if final_price < manual_discounted_price:
            # Offer is better
            total_offer += (original_price - final_price) * item.quantity
        elif item.product.discount_percentage:
            # Manual discount applied
            total_discount += (original_price - final_price) * item.quantity

    total_savings = total_offer + total_discount

    request.session['cart_total'] = str(grand_total)

    return render(request, 'user_app/cart.html', {
        'cart_items': cart_items,
        'grand_total': grand_total,
        'original_total': original_total,
        'total_discount': total_discount,
        'total_offer': total_offer,
        'total_savings': total_savings,
        'stock_info': stock_info,
    })
MAX_QUANTITY_PER_ITEM = getattr(settings, 'MAX_CART_ITEM_QUANTITY', 5)


@login_required
def add_to_cart(request, product_id):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request"}, status=400)

    product = get_object_or_404(Product, id=product_id, is_deleted=False)
    size = request.POST.get("size")
    quantity = int(request.POST.get("quantity", 1))

    if product.category and product.category.is_deleted:
        return JsonResponse({"status": "error", "message": "This product's category is not available."})

    try:
        size_stock = ProductSizeStock.objects.get(product=product, size=size)
    except ProductSizeStock.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Selected size is not available."})
 
    if size_stock.quantity <= 0:
        return JsonResponse({"status": "error", "message": "Out of stock."})

    quantity = min(quantity, size_stock.quantity, MAX_QUANTITY_PER_ITEM)

    cart_item, created = Cart.objects.get_or_create(
        user=request.user, product=product, size=size,
        defaults={'quantity': quantity}
    )
 
    if not created:
        new_quantity = cart_item.quantity + quantity
        max_allowed = min(size_stock.quantity, MAX_QUANTITY_PER_ITEM)
        if new_quantity <= max_allowed:
            cart_item.quantity = new_quantity
            cart_item.save()
            message = "Product quantity updated in cart."
        else:
            cart_item.quantity = max_allowed
            cart_item.save()
            message = "Maximum quantity reached for this item."
    else:
        message = "Product added to cart."

    Wishlist.objects.filter(user=request.user, product=product).delete()

    return JsonResponse({"status": "success", "message": message})


@login_required
def validate_cart_stock(request):
    cart_items = Cart.objects.filter(user=request.user)
    out_of_stock = []

    for item in cart_items:
        try:
            stock = ProductSizeStock.objects.get(product=item.product, size=item.size)
            if item.quantity > stock.quantity:
                out_of_stock.append({
                    'product': item.product.name,
                    'size': item.get_size_display(),
                    'available': stock.quantity
                })
        except ProductSizeStock.DoesNotExist:
            out_of_stock.append({
                'product': item.product.name,
                'size': item.get_size_display(),
                'available': 0
            })

    if out_of_stock:
        return JsonResponse({'status': 'error', 'items': out_of_stock})
    
    return JsonResponse({'status': 'ok'})

MAX_QUANTITY_PER_ITEM = 5

@login_required
def increment_quantity(request, item_id):
    if request.method != 'POST' or request.headers.get('x-requested-with') != 'XMLHttpRequest':
        return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

    cart_item = get_object_or_404(Cart, id=item_id, user=request.user)

    try:
        stock = ProductSizeStock.objects.get(product=cart_item.product, size=cart_item.size)
    except ProductSizeStock.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Stock info not found'})

    if cart_item.quantity >= MAX_QUANTITY_PER_ITEM:
        return JsonResponse({'status': 'warning', 'message': "Maximum 5 items allowed per product."})

    if cart_item.quantity >= stock.quantity:
        return JsonResponse({'status': 'warning', 'message': f"Only {stock.quantity} items left in stock."})

    cart_item.quantity += 1
    cart_item.save()

    # Recalculate all totals
    cart_items = Cart.objects.filter(user=request.user).select_related('product')
    subtotal = Decimal('0.00')
    total = Decimal('0.00')
    total_discount = Decimal('0.00')
    total_offer = Decimal('0.00')

    for item in cart_items:
        original_price = item.product.price
        manual_discounted_price = item.product.discounted_price
        final_price = item.product.final_price

        subtotal += original_price * item.quantity
        total += final_price * item.quantity

        if final_price < manual_discounted_price:
            # Offer applied
            total_offer += (original_price - final_price) * item.quantity
        elif item.product.discount_percentage:
            # Manual product discount
            total_discount += (original_price - final_price) * item.quantity

    return JsonResponse({
        'status': 'success',
        'item_id': cart_item.id,
        'new_quantity': cart_item.quantity,
        'item_total': float(cart_item.product.final_price * cart_item.quantity),
        'subtotal': float(subtotal),
        'discount': float(total_discount),
        'offer': float(total_offer),
        'grand_total': float(total),
        'available_stock': stock.quantity,
    })



@login_required
def decrement_quantity(request, item_id):
    if request.method != 'POST' or request.headers.get('x-requested-with') != 'XMLHttpRequest':
        return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

    cart_item = get_object_or_404(Cart, id=item_id, user=request.user)

    try:
        stock = ProductSizeStock.objects.get(product=cart_item.product, size=cart_item.size)
    except ProductSizeStock.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Stock info not found'})

    if cart_item.quantity <= 1:
        return JsonResponse({'status': 'warning', 'message': 'Minimum quantity is 1'})

    cart_item.quantity -= 1
    cart_item.save()

    # Recalculate all totals
    cart_items = Cart.objects.filter(user=request.user).select_related('product')
    subtotal = Decimal('0.00')
    total = Decimal('0.00')
    total_discount = Decimal('0.00')
    total_offer = Decimal('0.00')

    for item in cart_items:
        original_price = item.product.price
        manual_discounted_price = item.product.discounted_price
        final_price = item.product.final_price

        subtotal += original_price * item.quantity
        total += final_price * item.quantity

        if final_price < manual_discounted_price:
            total_offer += (original_price - final_price) * item.quantity
        elif item.product.discount_percentage:
            total_discount += (original_price - final_price) * item.quantity

    return JsonResponse({
        'status': 'success',
        'item_id': cart_item.id,
        'new_quantity': cart_item.quantity,
        'item_total': float(cart_item.product.final_price * cart_item.quantity),
        'subtotal': float(subtotal),
        'discount': float(total_discount),
        'offer': float(total_offer),
        'grand_total': float(total),
    })


@login_required
def remove_from_cart(request, item_id):
    Cart.objects.filter(id=item_id, user=request.user).delete()
    return redirect('/cart/?removed=true')

@login_required
def user_profile(request):
    user = request.user
    address = Address.objects.filter(user=user, is_default=True).first()

    if request.method == 'POST':
        form = ProfileImageForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile image updated successfully.")
            return redirect('user_profile')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = ProfileImageForm(instance=user)

    context = {
        'user': user,
        'address': address,
        'form': form  
    }
    return render(request, 'user_app/profile.html', context)

@login_required
def remove_profile_image(request):
    user = request.user
    if request.method == 'POST':
        if user.profile_image and user.profile_image.name != 'profiles/default.png':
            user.profile_image.delete(save=False)
        user.profile_image = 'profiles/default.png'
        user.save()
        messages.success(request, "Profile image removed.")
    return redirect('user_profile')



@login_required
def edit_profile(request):
    user = request.user
    address = Address.objects.filter(user=user, is_default=True).first()
    errors = {}

    if request.method == 'POST':
        full_name = request.POST.get('full_name').strip()
        phone = request.POST.get('phone').strip()
        street_address = request.POST.get('street_address').strip()

        if not full_name:
            errors['full_name'] = "Full name is required."
        elif not re.match(r'^(?=.*[a-zA-Z])[a-zA-Z0-9 _-]+$', full_name):
            errors['full_name'] = "Name must contain at least one letter and only use letters, numbers, spaces, hyphens, or underscores."
        elif full_name == "_" * len(full_name):
            errors['full_name']= "Username cannot be only underscores."
        elif CustomUser.objects.exclude(id=user.id).filter(username=full_name).exists():
            errors['full_name']='Username already exist.'
        if not phone:
            errors['phone']='Phone number is required'
        elif not phone.isdigit() or len(phone)!=10:
            errors['phone']='10 digits required'
        if not street_address:
            errors['street_address'] = "Street address is required."


        if errors:
            return render(request, 'user_app/edit_profile.html', {
                'address': address,
                'user': user,
                'errors': errors,
                'form_data': {
                    'full_name': full_name,
                    'phone': phone,
                    'street_address': street_address
                }
            })

        if " " in full_name:
            first_name, last_name = full_name.split(" ", 1)
        else:
            first_name = full_name
            last_name = ""

        user.first_name = first_name
        user.last_name = last_name
        user.save()

        if address:
            address.full_name = full_name
            address.mobile = phone
            address.street_address = street_address
            address.save()
        else:
            Address.objects.create(
                user=user,
                full_name=full_name,
                mobile=phone,
                email=user.email,
                street_address=street_address,
                district='Default',
                state='Default',
                country='Default',
                pincode=123456,
                is_default=True
            )

        messages.success(request, "Profile updated successfully.")
        return redirect('user_profile')

    return render(request, 'user_app/edit_profile.html', {
        'address': address,
        'user': user
    })


@login_required
def change_password(request):
    if not request.user.has_usable_password():
        messages.error(request, "Your account was created using Google login. Please use Google to sign in.", extra_tags='change_password')
        return redirect('user_profile')
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password was successfully updated!', extra_tags='change_password')
            return redirect('user_profile')  
        else:
            messages.error(request, 'Please correct the errors below.', extra_tags='change_password')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'user_app/change_password.html', {'form': form})


@login_required
def address_view(request):
    user = request.user
    addresses = Address.objects.filter(user=user)
    return render(request, 'user_app/address.html', {'addresses': addresses})


@login_required
def add_address(request):
    errors={}
    if request.method == 'POST':
        full_name = request.POST.get('full_name').strip()
        mobile = request.POST.get('mobile').strip()
        street = request.POST.get('street').strip()
        district = request.POST.get('district').strip()
        state = request.POST.get('state').strip()
        pincode = request.POST.get('pincode').strip()
        country = request.POST.get('country').strip()

        if not full_name:
            errors['full_name']='Name is required'
        elif not re.match(r'^(?=.*[a-zA-Z])[a-zA-Z0-9 _-]+$', full_name):
            errors['full_name'] = "Name must contain at least one letter and only use letters, numbers, spaces, hyphens, or underscores."
        elif full_name == "_" * len(full_name):
            errors['full_name']= "Username cannot be only underscores."
        if not mobile:
            errors['mobile']='Mobile number is required'
        elif not mobile.isdigit() or len(mobile)!=10:
            errors['mobile']='10 digits required'
        if not street:
            errors['street']='Street is required'
        if not district:
            errors['district']='District is required'
        if not state:
            errors['state']='State is required'
        if not pincode or len(pincode)!=6 or not pincode.isdigit():
            errors['pincode']='Pincode is required and it should be 6 digits'
        if not country:
            errors['country']='Country is required'
        if errors:
            return render(request,'user_app/add_address.html',{'errors':errors,
            'form_data': {
            'full_name': full_name,
            'mobile': mobile,
            'street': street,
            'district': district,
            'state': state,
            'pincode': pincode,
            'country': country
        }})
        

        
        is_first = not Address.objects.filter(user=request.user).exists()

        Address.objects.create(
            user=request.user,
            full_name=full_name,
            mobile=mobile,
            street_address=street,
            district=district,
            state=state,
            pincode=pincode,
            country=country,
            is_default=is_first  
        )

        messages.success(request, 'Address added successfully.')
        return redirect('address_view')

    return render(request, 'user_app/add_address.html')

@login_required
def edit_address(request, address_id):
    errors = {}
    address = get_object_or_404(Address, id=address_id, user=request.user)

    if request.method == 'POST':
        full_name = request.POST.get("full_name", "").strip()
        mobile = request.POST.get("mobile", "").strip()
        street = request.POST.get("street", "").strip()
        district = request.POST.get("district", "").strip()
        state = request.POST.get("state", "").strip()
        pincode = request.POST.get("pincode", "").strip()
        country = request.POST.get("country", "").strip()

        if not full_name:
            errors['full_name'] = 'Name is required'
        elif not re.match(r'^(?=.*[a-zA-Z])[a-zA-Z0-9 _-]+$', full_name):
            errors['full_name'] = "Name must contain at least one letter and only use letters, numbers, spaces, hyphens, or underscores."
        elif full_name == "_" * len(full_name):
            errors['full_name'] = "Username cannot be only underscores."

        if not mobile:
            errors['mobile'] = 'Mobile number is required'
        elif not mobile.isdigit() or len(mobile) != 10:
            errors['mobile'] = '10 digits required'

        if not street:
            errors['street'] = 'Street is required'
        if not district:
            errors['district'] = 'District is required'
        if not state:
            errors['state'] = 'State is required'
        if not pincode or not pincode.isdigit() or len(pincode) != 6:
            errors['pincode'] = 'Pincode is required and it should be 6 digits'
        if not country:
            errors['country'] = 'Country is required'

        if errors:
            return render(request, 'user_app/edit_address.html', {
                'errors': errors,
                'address': address
            })

        address.full_name = full_name
        address.mobile = mobile
        address.street_address = street
        address.district = district
        address.state = state
        address.pincode = pincode
        address.country = country
        address.save()

        messages.success(request, "Address updated successfully!")
        return redirect('address_view')

    return render(request, 'user_app/edit_address.html', {'address': address})


@login_required
def delete_address(request, address_id):
    address = get_object_or_404(Address, id=address_id, user=request.user)

    if address.is_default:
        next_address = Address.objects.filter(user=request.user).exclude(id=address_id).first()
        if next_address:
            next_address.is_default = True
            next_address.save()

    address.delete()
    messages.success(request, "Address deleted successfully.")
    return redirect('address_view')

@login_required
def checkout(request):
    cart_items = Cart.objects.filter(user=request.user).select_related('product')
    
    if not cart_items.exists():
        return redirect('cart_view')  # Prevent checkout on empty cart

    grand_total = Decimal('0.00')
    original_total = Decimal('0.00')
    total_discount = Decimal('0.00')

    for item in cart_items:
        discounted_price = item.product.final_price
        item.discounted_price = discounted_price
        item.total_price = discounted_price * item.quantity

        grand_total += item.total_price
        original_total += item.product.price * item.quantity
        total_discount += (item.product.price - discounted_price) * item.quantity

    request.session['cart_total'] = str(grand_total)

    addresses = Address.objects.filter(user=request.user)
    default_address = addresses.filter(is_default=True).first()

    shipping_charge = Decimal('0.00')

    # Get applied coupon
    coupon_code = request.session.get('applied_coupon_code')
    coupon_discount = Decimal(request.session.get('coupon_discount', '0.00'))

    final_total = (grand_total + shipping_charge) - coupon_discount

    # 🛑 Minimum amount check for Razorpay (₹1.00 = 100 paise)
    if final_total < Decimal('1.00'):
        # Clear any broken session coupon
        request.session.pop('applied_coupon_code', None)
        request.session.pop('coupon_discount', None)
        return redirect('cart')  # or show a message

    # ✅ Create Razorpay order
    razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    razorpay_order = razorpay_client.order.create({
        'amount': int(final_total * 100),  # in paise
        'currency': 'INR',
        'payment_capture': 1,
    })

    # Optionally clear previous razorpay session/order ID if stored
    request.session['razorpay_order_id'] = razorpay_order['id']

    valid_coupons = Coupon.objects.filter(
        active=True,
        valid_from__lte=timezone.now(),
        valid_to__gte=timezone.now(),
        minimum_order_amount__lte=grand_total
    )
    print("Valid coupons:", valid_coupons)


    context = {
        'cart_items': cart_items,
        'addresses': addresses,
        'default_address': default_address,
        'grand_total': grand_total,
        'original_total': original_total,
        'total_discount': total_discount,
        'shipping_charge': shipping_charge,
        'coupon_code': coupon_code,
        'coupon_discount': coupon_discount,
        'final_total': final_total,
        'has_addresses': addresses.exists(),
        'valid_coupons': valid_coupons,

        # Razorpay
        'razorpay_key': settings.RAZORPAY_KEY_ID,
        'razorpay_order': razorpay_order,
    }

    return render(request, 'user_app/checkout.html', context)


@login_required
@transaction.atomic
def place_order(request):
    if request.method != 'POST':
        return redirect('checkout')

    selected_address = request.POST.get('selected_address')
    payment_method = request.POST.get('payment_method')

    if not selected_address:
        return redirect('/checkout/?error=invalid_address')

    cart_items = Cart.objects.filter(user=request.user).select_related('product')
    if not cart_items.exists():
        return redirect('/checkout/?error=empty_cart')

    # Check stock
    for item in cart_items:
        try:
            stock = ProductSizeStock.objects.get(product=item.product, size=item.size)
            if item.quantity > stock.quantity:
                return redirect('/checkout/?stock_error=true')
        except ProductSizeStock.DoesNotExist:
            return redirect('/checkout/?stock_error=true')

    # Get or create address
    if selected_address != 'new':
        try:
            address = Address.objects.get(id=int(selected_address), user=request.user)
        except (ValueError, Address.DoesNotExist):
            return redirect('/checkout/?error=invalid_address')
    else:
        full_name = request.POST.get('full_name', '').strip()
        mobile = request.POST.get('mobile', '').strip()
        street = request.POST.get('street', '').strip()
        district = request.POST.get('district', '').strip()
        state = request.POST.get('state', '').strip()
        pincode = request.POST.get('pincode', '').strip()
        country = request.POST.get('country', '').strip()

        if not mobile or not mobile.isdigit() or len(mobile) != 10:
            return redirect('/checkout/?error=invalid_mobile')

        address = Address.objects.create(
            user=request.user,
            full_name=full_name,
            mobile=mobile,
            street_address=street,
            district=district,
            state=state,
            pincode=pincode,
            country=country,
            is_default=False
        )

    # Calculate totals
    grand_total = Decimal('0.00')
    for item in cart_items:
        grand_total += item.product.final_price * item.quantity

    # Coupon and shipping
    coupon_code = request.session.get('applied_coupon_code')
    coupon_discount = Decimal(request.session.get('coupon_discount', '0.00'))
    shipping_charge = Decimal('0.00')  # Add your own logic if needed

    final_total = (grand_total + shipping_charge) - coupon_discount

    # COD Limit Check
    if payment_method == "cod" and final_total > 10000:
        return redirect('/checkout/?error=cod_limit_exceeded')

    # Wallet check
    if payment_method == "wallet":
        wallet = request.user.wallet
        if wallet.balance < final_total:
            return redirect('/checkout/?error=wallet_insufficient')

    # Create Order
    order = Order.objects.create(
        user=request.user,
        order_id=get_random_string(10).upper(),
        status='PENDING',
        total_amount=final_total,
        full_name=address.full_name,
        mobile=address.mobile,
        street_address=address.street_address,
        district=address.district,
        state=address.state,
        pincode=address.pincode,
        country=address.country,
        address=address,
        payment_method=payment_method,
        payment_status='paid' if payment_method == 'wallet' else 'pending',
        coupon_code=coupon_code,
        coupon_discount=coupon_discount,
        shipping_charge=shipping_charge
    )

    # Handle wallet deduction
    if payment_method == "wallet":
        wallet.balance -= final_total
        wallet.save()

        WalletTransaction.objects.create(
            wallet=wallet,
            amount=final_total,
            transaction_type='DEBIT',
            description=f"Order #{order.order_id} payment"
        )

    # Create order items
    for item in cart_items:
        OrderItem.objects.create(
            order=order,
            product=item.product,
            quantity=item.quantity,
            size=item.size,
            price=item.product.final_price
        )

    # Reduce stock
    for item in cart_items:
        stock = ProductSizeStock.objects.get(product=item.product, size=item.size)
        stock.quantity -= item.quantity
        stock.save()

    # Clear cart
    if payment_method in ["cod", "wallet"]:
        cart_items.delete()


    # Clear coupon session
    request.session.pop('applied_coupon_code', None)
    request.session.pop('coupon_discount', None)

    # Handle Razorpay
    if payment_method == "razorpay":
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        razorpay_order = client.order.create({
            'amount': int(final_total * 100),  # paise
            'currency': 'INR',
            'payment_capture': 1
        })
        order.razorpay_order_id = razorpay_order['id']
        order.save()

        return render(request, 'user_app/razorpay_checkout.html', {
            'order': order,
            'razorpay_order': razorpay_order,
            'razorpay_key': settings.RAZORPAY_KEY_ID,
        })

    return redirect('order_success', order_id=order.id)

@login_required
def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'user_app/order_success.html', {'order': order})

login_required
def user_order_detail(request, order_id):
    order = Order.objects.select_related('address').get(id=order_id, user=request.user)
    return render(request, 'user_app/order_detail.html', {'order': order})

@login_required
def user_order_list(request):
    search_query = request.GET.get('q', '')
    
    # Fetch orders with related address and items
    orders = Order.objects.filter(user=request.user)\
        .select_related('address')\
        .prefetch_related('order_items')\
        .order_by('-created_at')

    if search_query:
        orders = orders.filter(order_id__icontains=search_query)

    enriched_orders = []
    for order in orders:
        items = order.order_items.all()
        total_items = items.count()

        approved_items = items.filter(is_return_approved=True).count()
        rejected_items = items.filter(is_return_rejected=True).count()
        requested_items = items.filter(is_return_requested=True).exists()

        # Default values
        order.status_display = order.get_status_display()
        order.status_class = "bg-yellow-100 text-yellow-700"

        if order.status == 'DELIVERED':
            if total_items == approved_items:
                order.status_display = "Return Accepted"
                order.status_class = "bg-green-100 text-green-700"
            elif rejected_items > 0:
                order.status_display = "Return Rejected"
                order.status_class = "bg-red-100 text-red-700"
            elif requested_items:
                order.status_display = "Return Requested"
                order.status_class = "bg-yellow-100 text-yellow-700"
            else:
                order.status_display = order.get_status_display()
                order.status_class = "bg-green-100 text-green-700"

        elif order.status == 'CANCELLED':
            order.status_display = order.get_status_display()
            order.status_class = "bg-red-100 text-red-700"

        enriched_orders.append(order)

    return render(request, 'user_app/order_list.html', {
        'orders': enriched_orders,
        'search_query': search_query
    })

@login_required
@transaction.atomic
def cancel_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    if order.status in ['DELIVERED', 'CANCELLED']:
        messages.error(request, "You cannot cancel this order.")
        return redirect('user_order_detail', order_id=order.id)

    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        order.status = 'CANCELLED'
        order.cancel_reason = reason
        order.save()

        for item in order.order_items.all():
            stock = ProductSizeStock.objects.get(product=item.product, size=item.size)
            stock.quantity += item.quantity
            stock.save()

        messages.success(request, "Order cancelled successfully.")
        return redirect('user_order_list')

    return render(request, 'user_app/cancel_order.html', {'order': order})

@login_required
def request_return(request, item_id):
    item = get_object_or_404(OrderItem, id=item_id, order__user=request.user)

    if item.order.status != 'DELIVERED' or item.is_return_requested:
        messages.error(request, "Return not allowed.")
        return redirect('user_order_detail', order_id=item.order.id)

    if request.method == 'POST':
        reason = request.POST.get('reason')
        if not reason:
            messages.error(request, "Reason is required.")
            return redirect('user_order_detail', order_id=item.order.id)

        item.is_return_requested = True  # ✅ fix here
        item.return_reason = reason
        item.return_requested_at = timezone.now()
        item.save()
        messages.success(request, "Return request submitted.")
        return redirect('user_order_detail', order_id=item.order.id)

    return render(request, 'user_app/return_item.html', {'item': item})


@login_required
def wallet_page(request):
    wallet = request.user.wallet
    transactions = wallet.transactions.all().order_by('-created_at')  # Fetch user's wallet transactions

    if request.method == "POST":
        try:
            amount = Decimal(request.POST.get('amount'))
            if amount > 0:
                wallet.balance += amount
                wallet.save()

                WalletTransaction.objects.create(
                    wallet=wallet,
                    amount=amount,
                    transaction_type='CREDIT',
                    description="Added to wallet"
                )

                messages.success(request, f"₹{amount} added to your wallet")
                return redirect('wallet_page')
            else:
                messages.error(request, 'Amount must be greater than 0.')
        except Exception as e:
            messages.error(request, 'Invalid amount')

    return render(request, 'user_app/wallet.html', {
        'wallet': wallet,
        'transactions': transactions  # Pass this to template
    })

@csrf_exempt
def payment_success(request):
    if request.method == "POST":
        data = json.loads(request.body)

        razorpay_order_id = data.get("razorpay_order_id")
        razorpay_payment_id = data.get("razorpay_payment_id")
        razorpay_signature = data.get("razorpay_signature")
        order_id = data.get("order_id")

        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        params_dict = {
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature
        }

        try:
            client.utility.verify_payment_signature(params_dict)

            order = Order.objects.get(id=order_id, razorpay_order_id=razorpay_order_id)

            if order.payment_status == "paid":
                return JsonResponse({"status": "already_paid", "order_id": order.id})

            # Update order payment info
            order.payment_status = "paid"
            order.razorpay_payment_id = razorpay_payment_id
            order.razorpay_signature = razorpay_signature
            order.status = "CONFIRMED"
            order.save()

            # Reduce stock
            for item in order.order_items.all():
                stock = ProductSizeStock.objects.get(product=item.product, size=item.size)
                stock.quantity -= item.quantity
                stock.save()

            # Clear user's cart
            Cart.objects.filter(user=order.user).delete()

            return JsonResponse({"status": "success", "order_id": order.id})

        except Exception as e:
            print("Signature verification failed:", e)
            return JsonResponse({"status": "failed"}, status=400)

    return JsonResponse({"status": "invalid"}, status=400)


def payment_failed(request):
    return render(request,'user_app/payment_failed.html')

@login_required
def download_invoice(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    template = get_template('user_app/invoice.html')
    html = template.render({'order': order})
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoice_{order.order_id}.pdf"'
    pisa.CreatePDF(html, dest=response)
    return response


@login_required
def apply_coupon(request):
    if request.method == "POST":
        code = request.POST.get('coupon_code', "").strip()
        if not code:
            messages.error(request, 'Please enter a coupon code.')
            return redirect('checkout')

        # Toggle logic: remove if same code is already applied
        if request.session.get('applied_coupon_code') == code:
            request.session.pop('applied_coupon_code', None)
            request.session.pop('coupon_discount', None)
            messages.info(request, f"Coupon '{code}' removed.")
            return redirect('checkout')

        # Apply new coupon
        try:
            coupon = Coupon.objects.get(code__iexact=code)

            if not coupon.is_valid():
                messages.error(request, 'Coupon is not valid.')
                return redirect('checkout')

            cart_items = Cart.objects.filter(user=request.user).select_related('product')
            cart_total = Decimal('0.00')
            for item in cart_items:
                cart_total += item.product.final_price * item.quantity

            if cart_total < coupon.minimum_order_amount:
                messages.error(request, f'Minimum order amount for this coupon is ₹{coupon.minimum_order_amount}.')
                return redirect('checkout')

            # Apply coupon
            best_discount = coupon.discount_amount
            request.session['applied_coupon_code'] = coupon.code
            request.session['coupon_discount'] = str(best_discount)
            messages.success(request, f"Coupon '{coupon.code}' applied! You saved ₹{best_discount:.2f}.")
            return redirect('checkout')

        except Coupon.DoesNotExist:
            messages.error(request, "Coupon does not exist.")
            return redirect('checkout')

    return redirect('checkout')
  

def custom_404(request, exception):
    return render(request, 'user_app/404.html', {
        'request_path': request.path,
    }, status=404)

@never_cache
def logout_view(request):
    logout(request)
    request.session.flush()
    list(messages.get_messages(request))
    return redirect('login')

