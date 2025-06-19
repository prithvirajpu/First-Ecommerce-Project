import random
import re
import time
import json

from django.http import JsonResponse
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

from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.messages import get_messages


from django.views.decorators.cache import never_cache

from django.core.paginator import Paginator
from decimal import Decimal
from .models import (
    Brand, Category, CustomUser, Product,
    ProductSizeStock, Address, EmailChangeToken,Wishlist,Cart,
    Order,OrderItem,Cart
)

from user_app.forms import LoginForm, ProfileImageForm 
from django.conf import settings
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils.crypto import get_random_string



@login_required
@csrf_exempt  # Optional: Use only if you're not sending the CSRF token in headers
def add_to_cart_from_wishlist(request, product_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            size = data.get('size')
            quantity = int(data.get('quantity', 1))

            product = Product.objects.get(id=product_id, is_deleted=False)

            cart_item, created = Cart.objects.get_or_create(
                user=request.user,
                product=product,
                size=size,
                defaults={'quantity': quantity}
            )

            if not created:
                cart_item.quantity += quantity
                cart_item.save()

            # ✅ Remove item from wishlist after adding to cart
            Wishlist.objects.filter(user=request.user, product=product).delete()

            return JsonResponse({'success': True})
        
        except Product.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Product not found'})
        
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})

    return JsonResponse({'success': False, 'message': 'Invalid request'}, status=400)

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

    # Remove from wishlist
    Wishlist.objects.filter(user=request.user, product=product).delete()

    return JsonResponse({"status": "success", "message": message})



@login_required
def cart_view(request):
    cart_items = Cart.objects.filter(user=request.user).select_related('product')
    grand_total = Decimal('0.00')

    for item in cart_items:
        try:
            stock = ProductSizeStock.objects.get(product=item.product, size=item.size)
            item.max_quantity = stock.quantity
        except ProductSizeStock.DoesNotExist:
            item.max_quantity = 0

        item.total_price = Decimal(item.product.price) * item.quantity
        grand_total += item.total_price

    return render(request, 'user_app/cart.html', {
        'cart_items': cart_items,
        'grand_total': grand_total
    })

@login_required
def increment_quantity(request, item_id):
    cart_item = get_object_or_404(Cart, id=item_id, user=request.user)

    try:
        stock = ProductSizeStock.objects.get(product=cart_item.product, size=cart_item.size)
    except ProductSizeStock.DoesNotExist:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'message': 'Stock info not found'})
        return redirect('cart_view')

    if cart_item.quantity >= stock.quantity:
        return JsonResponse({
            'status': 'error',
            'message': f"Only {stock.quantity} items left in stock"
        })

    if cart_item.quantity >= MAX_QUANTITY_PER_ITEM:
        return JsonResponse({
            'status': 'error',
            'message': f"Maximum limit per item is {MAX_QUANTITY_PER_ITEM}"
        })

    cart_item.quantity += 1
    cart_item.save()

    subtotal = sum(c.product.price * c.quantity for c in Cart.objects.filter(user=request.user))

    return JsonResponse({
        'status': 'success',
        'item_id': cart_item.id,
        'new_quantity': cart_item.quantity,
        'subtotal': f"{subtotal:.2f}",
    })


@login_required
def decrement_quantity(request, item_id):
    if request.method != 'POST' or request.headers.get('x-requested-with') != 'XMLHttpRequest':
        return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

    cart_item = get_object_or_404(Cart, id=item_id, user=request.user)

    if cart_item.quantity > 1:
        cart_item.quantity -= 1
        cart_item.save()
        new_quantity = cart_item.quantity
        deleted = False
    else:
        # Do not allow deleting, just return a warning
        return JsonResponse({
            'status': 'warning',
            'message': 'Minimum quantity is 1',
            'item_id': item_id,
            'new_quantity': 1,
            'deleted': False,
        })

    # Recalculate subtotal
    cart_items = Cart.objects.filter(user=request.user)
    subtotal = sum(item.product.price * item.quantity for item in cart_items)

    return JsonResponse({
        'status': 'success',
        'item_id': item_id,
        'new_quantity': new_quantity,
        'deleted': deleted,
        'subtotal': f"{subtotal:.2f}",
    })

@login_required
def remove_from_cart(request, item_id):
    Cart.objects.filter(id=item_id, user=request.user).delete()
    return redirect('/cart/?removed=true')

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

    # ✅ Get all wishlist product IDs for current user
    wishlist_products = []
    if request.user.is_authenticated:
        wishlist_products = Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True)

    context = {
        'best_selling_products': best_selling_products,
        'featured_products': featured_products,
        'wishlist_products': list(wishlist_products),  # important!
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
        products = products.filter(name__icontains =query )

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


@login_required
def user_profile(request):
    user = request.user
    address = Address.objects.filter(user=user, is_default=True).first()
    orders = Order.objects.filter(user=user).order_by('-created_at')  # latest first

    if request.method == 'POST':
        form = ProfileImageForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile image updated successfully.")
            return redirect('user_profile')
        else:
            # Show detailed form errors for debugging
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = ProfileImageForm(instance=user)

    context = {
        'user': user,
        'orders': orders,
        'address': address,
        'form': form  # ✅ important to pass form in context
    }
    return render(request, 'user_app/profile.html', context)

@login_required
def remove_profile_image(request):
    user = request.user
    if request.method == 'POST':
        if user.profile_image and user.profile_image.name != 'profiles/default_user.png':
            user.profile_image.delete(save=False)  # Delete image from disk
        user.profile_image = 'profiles/default.png'  # Reset to default image
        user.save()
        messages.success(request, "Profile image removed.")
    return redirect('user_profile')


@login_required
def verify_email_change(request, token):
    try:
        email_token = EmailChangeToken.objects.get(token=token, user=request.user)
    except EmailChangeToken.DoesNotExist:
        messages.error(request, "Invalid or expired verification link.")
        return redirect('user_profile')

    request.user.email = email_token.new_email
    request.user.save()
    email_token.delete()

    messages.success(request, "Your email address has been updated.")
    return redirect('user_profile')



@login_required
def edit_profile(request):
    user = request.user
    address = Address.objects.filter(user=user, is_default=True).first()
    errors = {}

    if request.method == 'POST':
        full_name = request.POST.get('full_name')
        phone = request.POST.get('phone')
        street_address = request.POST.get('street_address')

        # --- Validation ---
        if not full_name:
            errors['full_name'] = "Full name is required."

        if not phone or not phone.isdigit() or len(phone) != 10:
            errors['phone'] = "Enter a valid 10-digit phone number."

        if not street_address:
            errors['street_address'] = "Street address is required."

        # --- If any validation errors ---
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

        # --- Update user name ---
        if " " in full_name:
            first_name, last_name = full_name.split(" ", 1)
        else:
            first_name = full_name
            last_name = ""

        user.first_name = first_name
        user.last_name = last_name
        user.save()

        # --- Save or create default address ---
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

    # --- GET request ---
    return render(request, 'user_app/edit_profile.html', {
        'address': address,
        'user': user
    })


@login_required
def change_password(request):
    if not request.user.has_usable_password():
        messages.error(request, "Your account was created using Google login. Please use Google to sign in.", extra_tags='change_password')
        return redirect('user_profile')  # Or show a different page
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Important: Keep user logged in
            messages.success(request, 'Your password was successfully updated!', extra_tags='change_password')
            return redirect('user_profile')  # Redirect to profile or any success page
        else:
            messages.error(request, 'Please correct the errors below.', extra_tags='change_password')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'user_app/change_password.html', {'form': form})



@login_required
def address_view(request):
    user = request.user
    addresses = Address.objects.filter(user=user)

    if request.method == "POST":
        full_name = request.POST.get("full_name")
        mobile = request.POST.get("mobile")
        street = request.POST.get("street")
        district = request.POST.get("district")
        state = request.POST.get("state")
        pincode = request.POST.get("pincode")
        country = request.POST.get("country")

        # Make all existing addresses non-default
        Address.objects.filter(user=user).update(is_default=False)

        # Save the new address
        Address.objects.create(
            user=user,
            full_name=full_name,
            mobile=mobile,
            street_address=street,
            district=district,
            state=state,
            pincode=pincode,
            country=country,
            is_default=True,
        )
        messages.success(request, "Address added successfully!")
        return redirect('address_view')

    return render(request, 'user_app/address.html', {'addresses': addresses})


@login_required
def add_address(request):
    if request.method == 'POST':
        full_name = request.POST.get('full_name')
        mobile = request.POST.get('mobile')
        street = request.POST.get('street')
        district = request.POST.get('district')
        state = request.POST.get('state')
        pincode = request.POST.get('pincode')
        country = request.POST.get('country')

        if not all([full_name, mobile, street, district, state, pincode, country]):
            messages.error(request, 'All fields are required.')
            return redirect('add_address')

        Address.objects.create(
            user=request.user,
            full_name=full_name,
            mobile=mobile,
            street_address=street,
            district=district,
            state=state,
            pincode=pincode,
            country=country
        )

        messages.success(request, 'Address added successfully.')
        return redirect('address_view')

    return render(request, 'user_app/add_address.html')

@login_required
def edit_address(request, address_id):
    address = get_object_or_404(Address, id=address_id, user=request.user)

    if request.method == 'POST':
        address.full_name = request.POST.get("full_name")
        address.mobile = request.POST.get("mobile")
        address.street_address = request.POST.get("street")
        address.district = request.POST.get("district")
        address.state = request.POST.get("state")
        address.pincode = request.POST.get("pincode")
        address.country = request.POST.get("country")
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
    user = request.user
    cart_items = Cart.objects.filter(user=user)
    if not cart_items.exists():
        return redirect('cart_view')
    
    addresses = Address.objects.filter(user=user)

    default_address = addresses.filter(is_default=True).first()
    
    # Price calculations
    subtotal = sum(item.product.price * item.quantity for item in cart_items)

    shipping_charge = 0
    tax = 0
    total = subtotal + shipping_charge + tax

    context = {
        'cart_items': cart_items,
        'addresses': addresses,
        'default_address': default_address,
        'subtotal': subtotal,
        'tax': tax,
        'shipping': shipping_charge,
        'total': total,
    }

    return render(request, 'user_app/checkout.html', context)




@login_required
def place_order(request):
    if request.method == 'POST':
        address_type = request.POST.get('selected_address')

        # Get Cart Items
        cart_items = Cart.objects.filter(user=request.user)
        if not cart_items.exists():
            return redirect('/checkout/?error=empty_cart')

        # ✅ STOCK VALIDATION
        from user_app.models import ProductSizeStock  # adjust if needed
        out_of_stock_items = []
        for item in cart_items:
            try:
                stock = ProductSizeStock.objects.get(product=item.product, size=item.size)
                if item.quantity > stock.quantity:
                    out_of_stock_items.append(item.product.name)
            except ProductSizeStock.DoesNotExist:
                out_of_stock_items.append(item.product.name)

        if out_of_stock_items:
            # Redirect with stock error message
            return redirect('/checkout/?stock_error=true')

        # Address Handling
        if address_type != 'new':
            try:
                address = Address.objects.get(id=int(address_type), user=request.user)
            except (ValueError, Address.DoesNotExist):
                return redirect('/checkout/?error=invalid_address')
        else:
            full_name = request.POST.get('full_name')
            mobile = request.POST.get('mobile')
            street = request.POST.get('street')
            district = request.POST.get('district')
            state = request.POST.get('state')
            pincode = request.POST.get('pincode')
            country = request.POST.get('country')

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

        # Order Creation
        order = Order.objects.create(
            user=request.user,
            address=address,
            order_id=get_random_string(10).upper(),
            status='PENDING',
            total_amount=sum(item.product.price * item.quantity for item in cart_items)
        )

        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                size=item.size,
                price=item.product.price
            )

            stock = ProductSizeStock.objects.get(product=item.product, size=item.size)
            stock.quantity -= item.quantity
            stock.save()

        cart_items.delete()
        return redirect('order_success', order_id=order.id)

    return redirect('checkout')

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
    orders = Order.objects.filter(user=request.user).select_related('address').order_by('-created_at')
    return render(request, 'user_app/order_list.html', {'orders': orders})


@never_cache
def logout_view(request):
    logout(request)
    request.session.flush()
    list(messages.get_messages(request))
    return redirect('login')

