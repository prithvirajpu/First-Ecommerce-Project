from django.db import IntegrityError
from django.shortcuts import render, redirect,get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .forms import AdminLoginForm
from django.core.paginator import Paginator
from django.db.models import Q
from user_app.models import (CustomUser,Product, ProductImage, Category,
        Brand, ProductSizeStock,Order,OrderItem,Wallet)
from django.contrib.auth.decorators import user_passes_test
from django.views.decorators.cache import never_cache
import re


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
        price = request.POST.get('price')
        category_id = request.POST.get('category')
        brand_id = request.POST.get('brand')
        images = request.FILES.getlist('images')

        stock_s = request.POST.get('stock_S')
        stock_m = request.POST.get('stock_M')
        stock_l = request.POST.get('stock_L')
        discount_percentage = request.POST.get('discount_percentage')

        form_data = {
            'name': name,
            'description': description,
            'price': price,
            'category': category_id,
            'brand': brand_id,
            'stock_S': stock_s,
            'stock_M': stock_m,
            'stock_L': stock_l,
            'discount_percentage': discount_percentage,
        }

        # Validate discount
        try:
            discount_val = int(discount_percentage or 0)
            if not (0 <= discount_val <= 100):
                errors['discount_percentage'] = "Discount must be between 0 and 100"
        except (ValueError, TypeError):
            errors['discount_percentage'] = "Invalid discount value"

        # Validate name
        if not name:
            errors['name'] = 'Must enter the name'
        elif not re.match(r'^(?=.*[a-zA-Z])[a-zA-Z0-9 _-]+$', name):
            errors['name'] = "Please enter a product name with at least one letter. Only letters, numbers, spaces, hyphens, and underscores are allowed."
        elif name == "_" * len(name):
            errors['name'] = "Product name cannot be only underscores."
        elif Product.objects.filter(name__iexact=name).exists():
            errors['name'] = "The product name already exists"

        # Validate price
        try:
            price_val = float(price)
            if price_val <= 0:
                errors['price'] = "Price must be a positive number."
        except (ValueError, TypeError):
            errors['price'] = "Enter a valid number for price."

        # Validate stock
        try:
            s = int(stock_s)
            m = int(stock_m)
            l = int(stock_l)
            if s < 0 or m < 0 or l < 0:
                errors['stock_sizes'] = "Stock values must be non-negative."
        except:
            errors['stock_sizes'] = "All sizes (S, M, L) must have valid stock."

        # Validate category and brand
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

        # Validate images
        if len(images) < 3:
            errors['format'] = "Please upload at least 3 images."
        else:
            allowed_extensions = ['jpg', 'jpeg', 'png', 'webp', 'avif']
            for image in images:
                ext = image.name.split('.')[-1].lower()
                if ext not in allowed_extensions:
                    errors['format'] = "Invalid image file format"
                    break

        # Return form with errors
        if errors:
            print("FORM ERRORS:", errors)
            return render(request, 'user_app/add_product.html', {
                'categories': categories,
                'brands': brands,
                'errors': errors,
                'form_data': form_data
            })

        # ✅ All validations passed
        total_stock = s + m + l

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
            ProductSizeStock(product=product, size='S', quantity=s),
            ProductSizeStock(product=product, size='M', quantity=m),
            ProductSizeStock(product=product, size='L', quantity=l),
        ])

        messages.success(request, "Product added successfully.")
        return redirect('product_list')

    # GET method: render empty form
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
        price = request.POST.get('price')
        discount_percentage = request.POST.get('discount_percentage', '0') or '0'
        category_id = request.POST.get('category')
        brand_id = request.POST.get('brand')
        new_images = request.FILES.getlist('images')

        stock_s = request.POST.get('stock_S')
        stock_m = request.POST.get('stock_M')
        stock_l = request.POST.get('stock_L')

        form_data = {
            'name': name,
            'description': description,
            'price': price,
            'discount_percentage': discount_percentage,
            'stock_S': stock_s,
            'stock_M': stock_m,
            'stock_L': stock_l,
            'category_id': category_id,
            'brand_id': brand_id,
        }

        # Validate fields
        if not name:
            errors['name'] = 'Product name is required.'
        elif not re.match(r'^(?=.*[a-zA-Z])[a-zA-Z0-9 _-]+$', name):
            errors['name'] = (
                "Enter a valid product name (at least one letter, only letters, numbers, spaces, hyphens, underscores)."
            )
        elif name == "_" * len(name):
            errors['name'] = "Product name cannot be only underscores."

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

        # Stock Validation
        if not stock_s or not stock_m or not stock_l:
            errors['stock_sizes'] = "All sizes (S, M, L) must have stock."
        else:
            try:
                s = int(stock_s)
                m = int(stock_m)
                l = int(stock_l)
                if s < 0 or m < 0 or l < 0:
                    errors['stock_sizes'] = "Stock quantities must be non-negative."
            except ValueError:
                errors['stock_sizes'] = "Stock quantities must be integers."

        # Image validations
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

        # On error
        if errors:
            return render(request, 'user_app/edit_product.html', {
                'product': product,
                'categories': categories,
                'brands': brands,
                'errors': errors,
                'form_data': form_data,
                'images': existing_images,
                'stock': {
                    'stock_S': stock_s or size_stock.get('S', 0),
                    'stock_M': stock_m or size_stock.get('M', 0),
                    'stock_L': stock_l or size_stock.get('L', 0),
                }
            })

        # Save product
        product.name = name
        product.description = description
        product.price = price_val
        product.discount_percentage = discount_val
        product.category = category
        product.brand = brand
        product.stock = s + m + l
        product.save()

        # Update stock per size
        for size, quantity in [('S', s), ('M', m), ('L', l)]:
            ProductSizeStock.objects.update_or_create(
                product=product,
                size=size,
                defaults={'quantity': quantity}
            )

        # Replace images
        if new_images and len(new_images) == 3:
            for img in existing_images:
                if img.image:
                    img.image.delete(save=False)
                img.delete()
            for image in new_images:
                ProductImage.objects.create(product=product, image=image)

        messages.success(request, "Product updated successfully.")
        return redirect('product_list')

    # GET request
    form_data = {
        'name': product.name,
        'description': product.description,
        'price': product.price,
        'discount_percentage': product.discount_percentage,
        'stock_S': size_stock.get('S', 0),
        'stock_M': size_stock.get('M', 0),
        'stock_L': size_stock.get('L', 0),
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
            'stock_S': size_stock.get('S', 0),
            'stock_M': size_stock.get('M', 0),
            'stock_L': size_stock.get('L', 0),
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

    # Mark approved
    item.is_return_approved = True
    item.save()

    # Refund to wallet
    wallet, created = Wallet.objects.get_or_create(user=item.order.user)
    refund_amount = item.price * item.quantity
    wallet.balance += refund_amount
    wallet.save()

    messages.success(request, f"Return approved and ₹{refund_amount} refunded to user's wallet.")
    return redirect('admin_order_detail', order_id=item.order.id)

def admin_logout(request):
    logout(request)
    request.session.flush()  
    return redirect('admin_login')