from datetime import datetime, timedelta, timezone
from decimal import Decimal
from django.db import IntegrityError
from django.shortcuts import render, redirect,get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .forms import AdminLoginForm, ProductOfferForm,CategoryOfferForm
from django.core.paginator import Paginator
from django.db.models import Q,Sum, F, DecimalField, ExpressionWrapper, Count
from user_app.models import (Coupon, CustomUser,Product, ProductImage, Category,
        Brand, ProductSizeStock,Order,OrderItem,Wallet,ProductOffer, CategoryOffer, Product, Category, WalletTransaction)
from django.contrib.auth.decorators import user_passes_test
from django.views.decorators.cache import never_cache
import re
from django.utils import timezone


@never_cache
def admin_login(request):
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect('admin_dashboard')
    if request.user.is_authenticated:
        return redirect('user_dashboard')

    if request.method == 'POST':
        form = AdminLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None and user.is_superuser:
                login(request, user)
                return redirect('admin_dashboard')
            else:
                messages.error(request, "Invalid credentials or not an admin.")
                return redirect('admin_login')
    else:
        form = AdminLoginForm()

    return render(request, 'admin_app/admin_login.html', {'form': form})


@never_cache
@user_passes_test(lambda u: u.is_superuser, login_url='admin_login')
def admin_dashboard(request):
    return render(request, 'admin_app/admin_dashboard.html')


@never_cache
@user_passes_test(lambda u: u.is_superuser, login_url='admin_login')
def user_list(request):
    query=request.GET.get('q','')
    users=CustomUser.objects.filter(is_superuser=False).order_by('-date_joined')
    if query:
        users=users.filter(Q(username__icontains=query) | Q(email__icontains=query))

    paginator=Paginator(users,10)
    page_number=request.GET.get('page')
    page_obj=paginator.get_page(page_number)
    context={'users':page_obj,'query':query}
    return render(request,'admin_app/user_list.html',context)


@never_cache
@user_passes_test(lambda u: u.is_superuser, login_url='admin_login')
def block_user(request,user_id):
    user=get_object_or_404(CustomUser,id=user_id)
    user.is_blocked=True
    user.save()
    messages.success(request,f"{user.username} has been blocked.")
    return redirect('user_list')

@never_cache
@user_passes_test(lambda u: u.is_superuser, login_url='admin_login')
def unblock_user(request,user_id):
    user=get_object_or_404(CustomUser,id=user_id)
    user.is_blocked=False
    user.save()
    messages.success(request,f"{user.username} has been unblocked.")
    return redirect('user_list')

@never_cache
@user_passes_test(lambda u: u.is_superuser, login_url='admin_login')
def category_list(request):
    query = request.GET.get('q', '').strip()
    categories = Category.objects.all().order_by('-created_at')

    if query:
        categories = categories.filter(name__icontains=query)

    paginator = Paginator(categories, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'categories': page_obj,
        'query': query,
    }
    return render(request, 'admin_app/category_list.html', context)

@never_cache
@user_passes_test(lambda u: u.is_superuser, login_url='admin_login')
def add_category(request):
    errors = {}

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()

        if not name:
            errors['name'] = "Category name is required."
        elif not re.match(r'^(?=.*[a-zA-Z])[a-zA-Z0-9 _-]+$', name):
            errors['name'] = "Name must contain at least one letter and only use letters, numbers, spaces, hyphens, or underscores."
        elif name == "_" * len(name):
            errors['name']= "Username cannot be only underscores."
        elif Category.objects.filter(name__iexact=name).exists():
            errors['name'] = f'Category "{name}" already exists.'

        if not errors:
            try:
                Category.objects.create(name=name, description=description)
                messages.success(request, "Category added successfully.")
                return redirect('category_list')
            except IntegrityError:
                errors['name'] = f'Category "{name}" already exists.'

    return render(request, 'admin_app/add_category.html', {'errors': errors})

@never_cache
@user_passes_test(lambda u: u.is_superuser, login_url='admin_login')
def edit_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    errors = {}

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()

        if name == category.name and description == category.description:
            messages.info(request, "No changes detected.")
            return redirect('category_list')

        if not name:
            errors['name'] = "Category name is required."
        elif not re.match(r'^(?=.*[a-zA-Z])[a-zA-Z0-9 _-]+$', name):
            errors['name'] = "Name must contain at least one letter and only use letters, numbers, spaces, hyphens, or underscores."
        elif name == "_" * len(name):
            errors['name']= "Username cannot be only underscores."
        elif Category.objects.filter(name__iexact=name).exclude(id=category.id).exists():
            errors['name'] = f'Category \"{name}\" already exists.'
    
        if errors:
            return render(request, 'admin_app/edit_category.html', {
                'category': category,
                'errors': errors,
                'form_data': {
                    'name': name,
                    'description': description,
                }
            })

        category.name = name
        category.description = description
        category.save()
        messages.success(request, "Category updated successfully!")
        return redirect('category_list')

    return render(request, 'admin_app/edit_category.html', {'category': category})


@never_cache
@user_passes_test(lambda x:x.is_superuser,login_url='admin_login')
def toggle_category_status(request,category_id):
    category=get_object_or_404(Category,id=category_id)
    category.is_deleted=not category.is_deleted 
    category.save()
    status= "disabled" if category.is_deleted else "enabled"
    messages.success(request,f"Category {status} successfully")
    return redirect('category_list')


@never_cache
@user_passes_test(lambda u: u.is_superuser, login_url='admin_login')
def product_list(request):
    query = request.GET.get('q', '')  
    products = Product.objects.prefetch_related('size_stocks').order_by('-created_at')

    if query:
        products = products.filter(Q(name__icontains=query))

    paginator = Paginator(products, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'products': page_obj,
        'query': query
    }
    return render(request, 'user_app/product_list.html', context)


@never_cache
@user_passes_test(lambda u: u.is_superuser, login_url='admin_login')
def add_product(request):
    categories = Category.objects.filter(is_deleted=False)
    brands = Brand.objects.filter(is_active=True)
    errors = {}

    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        price = Decimal(request.POST.get('price') or 0)

        category_id = request.POST.get('category')
        brand_id = request.POST.get('brand')
        images = request.FILES.getlist('images')

        stock_6 = int(request.POST.get('stock_6') or 0)
        stock_7 = int(request.POST.get('stock_7') or 0)
        stock_8 = int(request.POST.get('stock_8') or 0)

        discount_str = request.POST.get('discount_percentage', '')
        discount_percentage = int(discount_str) if discount_str.isdigit() else 0


        form_data = {
            'name': name,
            'description': description,
            'price': price,
            'category': category_id,
            'brand': brand_id,
            'stock_6': stock_6,
            'stock_7': stock_7,
            'stock_8': stock_8,

            'discount_percentage': discount_percentage,
        }

        try:
            discount_val = int(discount_percentage or 0)
            if not (0 <= discount_val <= 100):
                errors['discount_percentage'] = "Discount must be between 0 and 100"
        except (ValueError, TypeError):
            errors['discount_percentage'] = "Invalid discount value"

        if not name:
            errors['name'] = 'Must enter the name'
        elif not re.match(r'^(?=.*[a-zA-Z])[a-zA-Z0-9 _-]+$', name):
            errors['name'] = "Please enter a product name with at least one letter. Only letters, numbers, spaces, hyphens, and underscores are allowed."
        elif name == "_" * len(name):
            errors['name'] = "Product name cannot be only underscores."
        elif Product.objects.filter(name__iexact=name).exists():
            errors['name'] = "The product name already exists"

        try:
            price_val = float(price)
            if price_val <= 0:
                errors['price'] = "Price must be a positive number."
        except (ValueError, TypeError):
            errors['price'] = "Enter a valid number for price."

        s6 = int(stock_6)
        s7 = int(stock_7)
        s8 = int(stock_8)
        if s6 < 0 or s7 < 0 or s8 < 0:
            errors['stock_sizes'] = "Stock values must be non-negative."

        try:
            category = Category.objects.get(id=category_id)
        except Category.DoesNotExist:
            errors['category'] = "Invalid category selected"
            category = None
        try:
            brand = Brand.objects.get(id=brand_id)
        except Brand.DoesNotExist:
            errors['brand'] = "Invalid brand selected"
            brand = None

        if len(images) < 3:
            errors['format'] = "Please upload at least 3 images."
        else:
            allowed_extensions = ['jpg', 'jpeg', 'png', 'webp', 'avif']
            for image in images:
                ext = image.name.split('.')[-1].lower()
                if ext not in allowed_extensions:
                    errors['format'] = "Invalid image file format"
                    break

        if errors:
            print("FORM ERRORS:", errors)
            return render(request, 'user_app/add_product.html', {
                'categories': categories,
                'brands': brands,
                'errors': errors,
                'form_data': form_data
            })

        total_stock = s6 + s7 + s8

        product = Product.objects.create(
            name=name,
            description=description,
            price=price_val,
            stock=total_stock,
            category=category,
            brand=brand,
            discount_percentage=discount_val,
        )

        for image in images:
            ProductImage.objects.create(product=product, image=image)

        ProductSizeStock.objects.bulk_create([
            ProductSizeStock(product=product, size='6', quantity=s6),
            ProductSizeStock(product=product, size='7', quantity=s7),
            ProductSizeStock(product=product, size='8', quantity=s8),
        ])

        messages.success(request, "Product added successfully.")
        return redirect('product_list')

    return render(request, 'user_app/add_product.html', {
        'categories': categories,
        'brands': brands,
        'errors': {},
        'form_data': {}
    })

@never_cache
@user_passes_test(lambda u: u.is_superuser, login_url='admin_login')
def edit_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    categories = Category.objects.filter(is_deleted=False)
    brands = Brand.objects.filter(is_active=True)
    existing_images = ProductImage.objects.filter(product=product)
    size_stock = {s.size: s.quantity for s in ProductSizeStock.objects.filter(product=product)}
    errors = {}

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        price = Decimal(request.POST.get('price')or 0)
        discount_percentage =int( request.POST.get('discount_percentage', '0') or '0')
        category_id = request.POST.get('category')
        brand_id = request.POST.get('brand')
        new_images = request.FILES.getlist('images')

        stock_6 = request.POST.get('stock_6', '0')
        stock_7 = request.POST.get('stock_7', '0')
        stock_8 = request.POST.get('stock_8', '0')

        form_data = {
            'name': name,
            'description': description,
            'price': price,
            'discount_percentage': discount_percentage,
            'stock_6': stock_6,
            'stock_7': stock_7,
            'stock_8': stock_8,
            'category_id': category_id,
            'brand_id': brand_id,
        }

        # --- Validation ---
        if not name:
            errors['name'] = 'Product name is required.'
        elif not re.match(r'^(?=.*[a-zA-Z])[a-zA-Z0-9 _-]+$', name):
            errors['name'] = "Enter a valid product name with at least one letter."
        elif name == "_" * len(name):
            errors['name'] = "Product name cannot be only underscores."
        elif Product.objects.exclude(id=product_id).filter(name__iexact=name).exists():
            errors['name'] = "The product name already exists"


        try:
            price_val = float(price)
            if price_val <= 0:
                errors['price'] = "Price must be a positive number."
        except (ValueError, TypeError):
            errors['price'] = "Enter a valid number for price."

        try:
            discount_val = int(discount_percentage)
            if not (0 <= discount_val <= 100):
                errors['discount_percentage'] = "Discount must be between 0 and 100."
        except ValueError:
            errors['discount_percentage'] = "Discount must be a valid integer."

        try:
            category = Category.objects.get(id=category_id)
        except (Category.DoesNotExist, ValueError, TypeError):
            errors['category'] = "Invalid category selected"
            category = None

        try:
            brand = Brand.objects.get(id=brand_id)
        except (Brand.DoesNotExist, ValueError, TypeError):
            errors['brand'] = "Invalid brand selected"
            brand = None

        try:
            s6 = int(stock_6)
            s7 = int(stock_7)
            s8 = int(stock_8)
            if s6 < 0 or s7 < 0 or s8 < 0:
                errors['stock_sizes'] = "Stock quantities must be non-negative."
        except:
            errors['stock_sizes'] = "All size fields must have valid stock quantities."

        allowed_extensions = ['jpg', 'jpeg', 'png', 'webp', 'avif']
        if new_images:
            if len(new_images) != 3:
                errors['format'] = "You must upload exactly 3 images to replace existing ones."
            else:
                for image in new_images:
                    ext = image.name.split('.')[-1].lower()
                    if ext not in allowed_extensions:
                        errors['format'] = "Invalid image format. Allowed: jpg, jpeg, png, webp, avif."
                        break
        else:
            if existing_images.count() != 3:
                errors['format'] = "Exactly 3 images are required. Please upload 3 images."

        # --- If Errors ---
        if errors:
            return render(request, 'user_app/edit_product.html', {
                'product': product,
                'categories': categories,
                'brands': brands,
                'errors': errors,
                'form_data': form_data,
                'images': existing_images,
                'stock': {
                    'stock_6': stock_6 or size_stock.get('6', 0),
                    'stock_7': stock_7 or size_stock.get('7', 0),
                    'stock_8': stock_8 or size_stock.get('8', 0),
                }
            })

        # --- Update Product ---
        product.name = name
        product.description = description
        product.price = price_val
        product.discount_percentage = discount_val
        product.category = category
        product.brand = brand
        product.stock = s6 + s7 + s8
        product.save()

        for size, quantity in [('6', s6), ('7', s7), ('8', s8)]:
            ProductSizeStock.objects.update_or_create(
                product=product,
                size=size,
                defaults={'quantity': quantity}
            )

        if new_images and len(new_images) == 3:
            for img in existing_images:
                if img.image:
                    img.image.delete(save=False)
                img.delete()
            for image in new_images:
                ProductImage.objects.create(product=product, image=image)

        messages.success(request, "Product updated successfully.")
        return redirect('product_list')

    # --- GET Request (prefill form) ---
    form_data = {
        'name': product.name,
        'description': product.description,
        'price': product.price,
        'discount_percentage': product.discount_percentage,
        'stock_6': size_stock.get('6', 0),
        'stock_7': size_stock.get('7', 0),
        'stock_8': size_stock.get('8', 0),
        'category_id': product.category.id if product.category else None,
        'brand_id': product.brand.id if product.brand else None,
    }

    return render(request, 'user_app/edit_product.html', {
        'product': product,
        'categories': categories,
        'brands': brands,
        'errors': {},
        'form_data': form_data,
        'images': existing_images,
        'stock': {
            'stock_6': size_stock.get('6', 0),
            'stock_7': size_stock.get('7', 0),
            'stock_8': size_stock.get('8', 0),
        }
    })


@never_cache
@user_passes_test(lambda x: x.is_superuser, login_url='admin_login')
def toggle_product_status(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product.is_deleted = not product.is_deleted
    product.save()
    
    status = "disabled" if product.is_deleted else "enabled"
    messages.success(request, f"Product {status} successfully.")
    
    return redirect('product_list')


@never_cache
@user_passes_test(lambda u: u.is_superuser, login_url='admin_login')
def brand_list(request):
    brands=Brand.objects.all().order_by('-created_at')
    context={'brands':brands}
    return render(request,'user_app/brand_list.html',context)
@never_cache
@user_passes_test(lambda u: u.is_superuser, login_url='admin_login')
def add_brand(request):
    errors = {}
    form_data = {}

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        logo = request.FILES.get('logo')
        status = request.POST.get('status') 

        form_data['name'] = name
        form_data['description'] = description

        if not name:
            errors['name'] = 'Must enter the name.'
        elif name == "_" * len(name):
            errors['name']= "Username cannot be only underscores."
        elif not re.match(r'^(?=.*[a-zA-Z])[a-zA-Z0-9 _-]+$', name):
            errors['name'] = (
                "Please enter a brand name with at least one letter. "
                "Only letters, numbers, spaces, hyphens, and underscores are allowed."
            )
        elif Brand.objects.filter(name__iexact=name).exists():
            errors['name'] = "The brand name already exists."

        if not logo:
            errors['logo'] = "Brand logo is required."
        else:
            ext = logo.name.split('.')[-1].lower()
            if ext not in ['jpg', 'jpeg', 'png', 'webp']:
                errors['logo'] = "Only JPG, JPEG, PNG, or WEBP images are allowed."

        if errors:
            return render(request, 'user_app/add_brand.html', {'errors': errors, 'form_data': form_data})
        status = True if status== 'active' else False
        Brand.objects.create(
            name=name,
            description=description,
            logo=logo,
            status=status
        )

        messages.success(request, "Brand created successfully.", extra_tags="brand success")
        return redirect('brand_list')

    return render(request, 'user_app/add_brand.html', {'errors': {}, 'form_data': {}})

@never_cache
@user_passes_test(lambda u: u.is_superuser, login_url='admin_login')
def edit_brand(request, brand_id):
    brand = get_object_or_404(Brand, id=brand_id)
    errors = {}
    form_data = {}

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        logo = request.FILES.get('logo')

        form_data = {
            'name': name,
            'description': description,
        }
 
        if not re.match(r'^[A-Za-z]+(?: [A-Za-z]+)*$', name):
            errors['name'] = "Brand name should only contain letters and spaces, without leading/trailing spaces or underscores."

        elif name == "_" * len(name):
            errors['name']= "Username cannot be only underscores."
        elif name.lower() != brand.name.lower():
            if Brand.objects.filter(name__iexact=name).exclude(id=brand.id).exists():
                errors['name'] = "This brand name already exists."

        if logo:
            ext = logo.name.split('.')[-1].lower()
            if ext not in ['jpg', 'jpeg', 'png', 'webp']:
                errors['logo'] = "Only JPG, JPEG, PNG, or WEBP images are allowed."

        if errors:
            return render(request, 'user_app/edit_brand.html', {
                'brand': brand,
                'errors': errors,
                'form_data': form_data
            })

        changes = False
        if name != brand.name:
            brand.name = name
            changes = True
        if description != brand.description:
            brand.description = description
            changes = True
        if logo:
            brand.logo = logo
            changes = True

        if changes:
            brand.save()
            messages.success(request, "Brand updated successfully.", extra_tags="brand success")
        else:
            messages.info(request, "No changes were made.", extra_tags="brand info")

        return redirect('brand_list')

    return render(request, 'user_app/edit_brand.html', {'brand': brand})


@never_cache
@user_passes_test(lambda u: u.is_superuser, login_url='admin_login')
def toggle_brand_status(request, brand_id):
    brand = get_object_or_404(Brand, id=brand_id)
    brand.is_active =  not brand.is_active
    brand.save()
    return redirect('brand_list')

@never_cache
@user_passes_test(lambda x: x.is_superuser, login_url='admin_login')
def admin_order_list(request):
    query=request.GET.get('q','')
    status_filter=request.GET.get('status','')
    orders=Order.objects.select_related('user').order_by('-created_at')

    if query:
        orders=orders.filter(Q (order_id__icontains=query) | 
                            Q (user__email__icontails=query)|
                            Q (user__full_name__icontains=query))
    if status_filter:
        orders=orders.filter(status=status_filter)
    paginator=Paginator(orders,10)
    page=request.GET.get('page')
    order_page=paginator.get_page(page)
    context={'orders':order_page,
             'query':query,
             'status_filter':status_filter}
    return render(request,'admin_app/order_list.html',context)



@never_cache
@user_passes_test(lambda x: x.is_superuser, login_url='admin_login')
def admin_order_detail(request,order_id):
    order=get_object_or_404(Order.objects.select_related('user','address'),id=order_id)
    items=order.order_items.select_related('product')
    context={'order':order,
             'items':items}
    return render(request,'admin_app/order_detail.html',context)


@never_cache
@user_passes_test(lambda x: x.is_superuser, login_url='admin_login')
def admin_update_order_status(request, order_id):
    if request.method == "POST":
        order = get_object_or_404(Order, id=order_id)
        new_status = request.POST.get("status")

        if new_status in dict(Order.STATUS_CHOICES).keys():
            order.status = new_status

            # ✅ Update payment status if delivered
            if new_status == 'DELIVERED' and order.payment_method in ['cod', 'wallet']:
                order.payment_status = 'paid'

            order.save()
            messages.success(request, f"Order status updated to {order.get_status_display()}.")
        else:
            messages.error(request, "Invalid status selected.")

    return redirect('admin_order_detail', order_id=order_id)

@never_cache
@user_passes_test(lambda x: x.is_superuser, login_url='admin_login')
def approve_return(request, order_item_id):
    item = get_object_or_404(OrderItem, id=order_item_id)

    if not item.is_return_requested or item.is_return_approved:
        messages.warning(request, "Invalid or already approved return request.")
        return redirect('admin_order_detail', order_id=item.order.id)

    item.is_return_approved = True
    item.status = 'RETURN_ACCEPTED'
    item.save()

    # ✅ Update stock
    try:
        stock_obj = ProductSizeStock.objects.get(product=item.product, size=item.size)
        stock_obj.quantity += item.quantity
        stock_obj.save()
    except ProductSizeStock.DoesNotExist:
        messages.warning(request, f"Stock entry for size {item.size} not found. Please add it manually.")

    # ✅ Refund to wallet
    wallet, created = Wallet.objects.get_or_create(user=item.order.user)
    refund_amount = item.price * item.quantity
    wallet.balance += refund_amount
    wallet.save()

    # ✅ Create wallet transaction log
    WalletTransaction.objects.create(
        wallet=wallet,
        amount=refund_amount,
        transaction_type='CREDIT',
        description=f"Refund for return: {item.product.name} (Size {item.size})"
    )

    messages.success(request, f"Return approved and ₹{refund_amount} refunded to user's wallet.")
    return redirect('admin_order_detail', order_id=item.order.id)

@user_passes_test(lambda x: x.is_superuser)
def reject_return(request, order_item_id):
    item = get_object_or_404(OrderItem, id=order_item_id)

    if item.is_return_requested and not item.is_return_approved:
        item.is_return_rejected = True
        item.return_rejected_reason = "Rejected by admin"
        item.save()
        messages.success(request, "Return request rejected.")
    else:
        messages.warning(request, "Return request not pending or already handled.")

    return redirect('admin_order_detail', order_id=item.order.id)

@user_passes_test(lambda x: x.is_superuser)
def list_offers(request):
    product_offers=ProductOffer.objects.prefetch_related('products').all()
    category_offers=CategoryOffer.objects.prefetch_related('categories').all()
    return render(request,'admin_app/list_offers.html',{
        'product_offers':product_offers,
        'category_offers':category_offers,
    })

@user_passes_test(lambda x: x.is_superuser)
def add_product_offer(request):
    if request.method == "POST":
        form = ProductOfferForm(request.POST)
        if form.is_valid():
            offer = form.save(commit=False)
            offer.save()
            form.save_m2m()  # This is necessary for ManyToManyField
            messages.success(request, 'Product offer added successfully.')
            return redirect('list_offers')
    else:
        form = ProductOfferForm()
        
    return render(request, 'admin_app/add_product_offer.html', {
        'form': form
    })

@user_passes_test(lambda x: x.is_superuser)
def edit_product_offer(request, offer_id):
    offer = get_object_or_404(ProductOffer, id=offer_id)
    
    if request.method == 'POST':
        form = ProductOfferForm(request.POST, instance=offer)
        if form.is_valid():
            form.save()  # or form.save(commit=False) + form.save_m2m() if needed
            messages.success(request, 'Product offer updated successfully.')
            return redirect('list_offers')
    else:
        # ✅ Important: include the instance when showing the form initially
        form = ProductOfferForm(instance=offer)
    
    return render(request, 'admin_app/edit_offer.html', {
        'form': form,
        'offer_type': 'Product',
        'offer': offer,  # if you're using offer.name or ID in template
    })

@user_passes_test(lambda x:x.is_superuser)
def delete_product_offer(request,offer_id):
    val=get_object_or_404(ProductOffer,id=offer_id)
    val.is_active=not val.is_active
    val.save()
    status='enabled' if val.is_active else 'disabled'
    messages.success(request,f'Offer has been {status} successfully.')
    return redirect('list_offers')


@user_passes_test(lambda x: x.is_superuser)
def add_category_offer(request):
    if request.method == "POST":
        form = CategoryOfferForm(request.POST)
        if form.is_valid():
            offer = form.save(commit=False)  # First save the main object
            offer.save()
            form.save_m2m()  # Then save the many-to-many relationship
            messages.success(request, 'Category offer added successfully.')
            return redirect('list_offers')
    else:
        form = CategoryOfferForm()
    return render(request, 'admin_app/add_category_offer.html', {'form': form})

@user_passes_test(lambda x: x.is_superuser)
def edit_category_offer(request, offer_id):
    offer = get_object_or_404(CategoryOffer, id=offer_id)

    if request.method == 'POST':
        form = CategoryOfferForm(request.POST, instance=offer)
        if form.is_valid():
            offer = form.save(commit=False)
            offer.save()
            form.save_m2m()
            messages.success(request, 'Category offer updated successfully.')
            return redirect('list_offers')
    else:
        form = CategoryOfferForm(instance=offer)

    # Like product offer: manually pass selected/unselected categories
    form.selected_categories = offer.categories.all()
    from user_app.models import Category  # adjust if your Category model is elsewhere
    form.unselected_categories = Category.objects.exclude(id__in=offer.categories.values_list('id', flat=True))

    return render(request, 'admin_app/edit_offer.html', {
        'form': form,
        'offer_type': 'Category',
        'offer': offer,
    })

@user_passes_test(lambda x: x.is_superuser)
def delete_category_offer(request,offer_id):
    val=get_object_or_404(CategoryOffer,id=offer_id)
    val.is_active=not val.is_active
    val.save()
    status='enabled' if val.is_active else 'disabled'
    messages.success(request,f'Offer  has been {status} successfully')
    return redirect('list_offers')

@user_passes_test(lambda x: x.is_superuser)
def admin_coupon_list(request):
    coupons=Coupon.objects.all().order_by('-valid_to')
    return render(request,'admin_app/admin_coupon_list.html',{'coupons':coupons})

@user_passes_test(lambda x: x.is_superuser)
def add_coupon(request):
    form={}
    error = {}
    if request.method == 'POST':
        code = request.POST.get('code', '').strip()
        discount_amount = request.POST.get('discount_amount', '').strip()
        minimum_order_amount = request.POST.get('minimum_order_amount', '').strip()
        valid_from = request.POST.get('valid_from', '').strip()
        valid_to = request.POST.get('valid_to', '').strip()
        active = request.POST.get('active') == 'on'

        # CODE validation
        if not code:
            error['code'] = 'Coupon code is required.'
        elif re.fullmatch(r'_+', code):
            error['code'] = 'Coupon code cannot be only underscores.'
        elif code.isdigit():
            error['code'] = 'Coupon code cannot be only digits.'
        elif not re.match(r'^[A-Za-z0-9_-]+$', code):
            error['code'] = 'Coupon code can only contain letters, numbers, dashes, and underscores.'

        # DISCOUNT_AMOUNT validation
        if not discount_amount:
            error['discount_amount'] = 'Discount amount is required.'
        else:
            try:
                discount_amount = float(discount_amount)
                if discount_amount <= 0:
                    error['discount_amount'] = 'Discount must be greater than zero.'
            except ValueError:
                error['discount_amount'] = 'Discount must be a number.'

        # MINIMUM_ORDER_AMOUNT validation
        if not minimum_order_amount:
            error['minimum_order_amount'] = 'Minimum order amount is required.'
        else:
            try:
                minimum_order_amount = float(minimum_order_amount)
                if minimum_order_amount <= 0:
                    error['minimum_order_amount'] = 'Minimum order must be greater than zero.'
            except ValueError:
                error['minimum_order_amount'] = 'Minimum order must be a number.'

        # DATE validation
        date_format = '%Y-%m-%d'
        try:
            valid_from_date = datetime.strptime(valid_from, date_format)
        except ValueError:
            error['valid_from'] = 'Invalid start date format (YYYY-MM-DD).'

        try:
            valid_to_date = datetime.strptime(valid_to, date_format)
        except ValueError:
            error['valid_to'] = 'Invalid end date format (YYYY-MM-DD).'

        # Compare dates only if both are valid
        if 'valid_from' not in error and 'valid_to' not in error:
            if valid_to_date < valid_from_date:
                error['valid_to'] = 'End date cannot be before start date.'
        
        # Final creation if no errors
        if not error:
            Coupon.objects.create(
                code=code,
                discount_amount=discount_amount,
                minimum_order_amount=minimum_order_amount,
                valid_from=valid_from_date,
                valid_to=valid_to_date,
                active=active
            )
            messages.success(request, 'Coupon created successfully.')
            return redirect('admin_coupon_list')
        form={'code':code,
                'discount_amount':discount_amount,
                'minimum_order_amount':minimum_order_amount,
                'valid_from':valid_from_date,
                'valid_to':valid_to_date,
                'active':active}

    return render(request, 'admin_app/admin_add_coupon.html', {'error': error,'form':form})

@user_passes_test(lambda x:x.is_superuser)
def edit_coupon(request,coupon_id):
    coupon=get_object_or_404(Coupon,id=coupon_id)
    error={}
    if request.method=="POST":
        code=request.POST.get('code','').strip()
        discount_amount=request.POST.get('discount_amount','').strip()
        minimum_order_amount=request.POST.get('minimum_order_amount','').strip()
        valid_from=request.POST.get('valid_from','').strip()
        valid_to=request.POST.get('valid_to','').strip()
        active=True if request.POST.get('is_active') else False
        if Coupon.objects.exclude(id=coupon_id).filter(code__iexact=code).exists():
            error['exist']='This is already exist.'
        if not code:
            error['code']='"Coupon code is required.'
        elif re.fullmatch(r'_+',code):
            error['code']="Coupon code can't be only underscores. "
        elif code.isdigit():
            error['code']="Coupon code can't be only digits"
        if not discount_amount:
            error['discount_amount']='Discount amount is required.'
        else:
            try:
                discount_amount=float(discount_amount)
                if discount_amount<0:
                    error['discount_amount']='Discount amount should be more than 0'
            except ValueError:
                error['discount_amount']='Discount amount should be number'
        if not discount_amount:
            error['discount_amount']='Discount amount is required.'
        else:
            try:
                minimum_order_amount=float(minimum_order_amount)
                if minimum_order_amount<0:
                    error['minimum_order_amount']='Discount amount should be more than 0'
            except ValueError:
                error['minimum_order_amount']='Discount amount should be number'
        

        coupon.code=code
        coupon.discount_amount=discount_amount
        coupon.minimum_order_amount=minimum_order_amount
        coupon.valid_from=valid_from
        coupon.valid_to=valid_to
        coupon.active=active
        coupon.save()       

        messages.success(request,'Coupon updated successfully.')
        return redirect('admin_coupon_list')
    form={
        'code':coupon.code,
        'discount_amount':coupon.discount_amount,
        'minimum_order_amount' :coupon.minimum_order_amount,
            'valid_from':coupon.valid_from,
            'valid_to':coupon.valid_to,
           'active': coupon.active
    }
    return render(request,'admin_app/admin_edit_coupon.html',{'form':form,'coupon':coupon,'error':error})

@user_passes_test(lambda x: x.is_superuser)
def toggle_coupon(request,coupon_id):
    val=get_object_or_404(Coupon,id=coupon_id)
    val.active=not val.active
    val.save()
    status='Disabled' if val.active else 'Enabled'
    messages.success(request,f'Coupon has been {status} successfully.')
    return redirect('admin_coupon_list')

@user_passes_test(lambda x: x.is_superuser)
def sales_report(request):
    today=timezone.now()
    filter_type=request.GET.get('filter','today')
    from_date=request.GET.get('from_date')
    to_date=request.GET.get('to_date')

    start_date=end_date=today
    if filter_type=='today':
        start_date=end_date=today
    elif filter_type=='week':
        start_date=today-timedelta(days=7)
        end_date=today
    elif filter_type=='month':
        start_date=today.replace(day=1)
        end_date=today
    elif filter_type == 'year':
        start_date = today.replace(month=1, day=1)
        end_date = today
    orders = Order.objects.filter(
            created_at__date__range=(start_date, end_date),
            payment_status='paid',
            status='DELIVERED'
        )

    total_orders = orders.count()
    total_discount = orders.aggregate(total=Sum('coupon_discount'))['total'] or 0
    total_order_amount = orders.aggregate(total=Sum('total_amount'))['total'] or 0

    order_items = OrderItem.objects.filter(order__in=orders)
    total_quantity = order_items.aggregate(qty=Sum('quantity'))['qty'] or 0
    total_item_sales = order_items.annotate(
        total_price=ExpressionWrapper(F('quantity') * F('price'), output_field=DecimalField())
    ).aggregate(sales=Sum('total_price'))['sales'] or 0

    context = {
            'orders': orders,
            'total_orders': total_orders,
            'total_discount': total_discount,
            'total_order_amount': total_order_amount,
            'total_quantity': total_quantity,
            'total_item_sales': total_item_sales,
            'filter_type': filter_type,
            'from_date': start_date,
            'to_date': end_date,
        }
    return render(request, 'admin_app/sales_report.html', context)


def admin_logout(request):
    logout(request)
    request.session.flush()  
    return redirect('admin_login')