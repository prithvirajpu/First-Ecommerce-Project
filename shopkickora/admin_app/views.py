from django.db import IntegrityError
from django.shortcuts import render, redirect,get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .forms import AdminLoginForm
from django.core.paginator import Paginator
from django.db.models import Q
from user_app.models import CustomUser,Product, ProductImage, Category, Brand, ProductSizeStock
from django.contrib.auth.decorators import user_passes_test 
from django.views.decorators.cache import never_cache
import re



@never_cache
def admin_login(request):
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect('admin_dashboard')


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
    print("Logged in user:", request.user)
    return render(request, 'admin_app/admin_dashboard.html')


def admin_logout(request):
    logout(request)
    request.session.flush()  
    return redirect('admin_login')

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

        # Check for no changes
        if name == category.name and description == category.description:
            messages.info(request, "No changes detected.")
            return redirect('category_list')

        # Validations
        if not name:
            errors['name'] = "Category name is required."
        elif not re.match(r'^(?=.*[a-zA-Z])[a-zA-Z0-9 _-]+$', name):
            errors['name'] = "Name must contain at least one letter and only use letters, numbers, spaces, hyphens, or underscores."
        elif '__' in name:
            errors['name'] = "Category name cannot contain consecutive underscores (e.g., '__')."
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

        # If everything is valid, update and save
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
    status= "enabled" if category.is_deleted else "disabled"
    messages.success(request,f"Category {status} successfully")
    return redirect('category_list')



@never_cache
@user_passes_test(lambda u: u.is_superuser, login_url='admin_login')
def product_list(request):
    query = request.GET.get('q', '')  # Search query

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
    brands = Brand.objects.filter(status='active')
    errors = {}

    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        price = request.POST.get('price')
        category_id = request.POST.get('category')
        brand_id = request.POST.get('brand')
        images = request.FILES.getlist('images')

        # ✅ Size-based stock inputs
        stock_s = request.POST.get('stock_S')
        stock_m = request.POST.get('stock_M')
        stock_l = request.POST.get('stock_L')

        form_data = {
            'name': name,
            'description': description,
            'price': price,
            'category_id': category_id,
            'brand_id': brand_id,
            'stock_S': stock_s,  # ✅
            'stock_M': stock_m,  # ✅
            'stock_L': stock_l,  # ✅
        }

        # ✅ Check image count
        if len(images) < 3:
            errors['format'] = "Please upload at least 3 images."

        # ✅ Product name validation
        allowed_extensions = ['jpg', 'jpeg', 'png', 'webp']
        if not name:
            errors['name'] = 'Must enter the name'
        elif not re.match(r'^(?=.*[a-zA-Z])[a-zA-Z0-9 _-]+$', name):
            errors['name'] = ("Please enter a product name with at least one letter. "
                              "Only letters, numbers, spaces, hyphens, and underscores are allowed.")
        elif Product.objects.filter(name__iexact=name).exists():
            errors['name'] = "The product name already exists"

        # ✅ Image extension validation
        for image in images:
            ext = image.name.split('.')[-1].lower()
            if ext not in allowed_extensions:
                errors['format'] = "Invalid file format"
                break

        # ✅ Price validation
        try:
            price_val = float(price)
            if price_val <= 0:
                errors['price'] = "Price must be a positive number."
        except (ValueError, TypeError):
            errors['price'] = "Enter a valid number for price."

        # ✅ Validate size stock
        if not stock_s or not stock_m or not stock_l:
            errors['stock_sizes'] = "All sizes (S, M, L) must have stock."
        try:
            s = int(stock_s)
            m = int(stock_m)
            l = int(stock_l)
            if s < 0 or m < 0 or l < 0:
                errors['stock_sizes'] = "Stock values cannot be negative."
        except:
            errors['stock_sizes'] = "Stock values must be integers."

        # ✅ Validate category and brand
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

        if errors:
            return render(request, 'user_app/add_product.html', {
                'categories': categories,
                'brands': brands,
                'errors': errors,
                'form_data': form_data
            })

        # ✅ Total stock is sum of S, M, L
        total_stock = int(stock_s) + int(stock_m) + int(stock_l)

        product = Product.objects.create(
            name=name,
            description=description,
            price=price,
            stock=total_stock,
            category=category,
            brand=brand
        )

        for image in images:
            ProductImage.objects.create(product=product, image=image)

        # ✅ Create ProductSizeStock entries
        ProductSizeStock.objects.bulk_create([
    ProductSizeStock(product=product, size='S', quantity=s),
    ProductSizeStock(product=product, size='M', quantity=m),
    ProductSizeStock(product=product, size='L', quantity=l),
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
    brands = Brand.objects.filter(status='active')
    existing_images = ProductImage.objects.filter(product=product)
    errors = {}

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        price = request.POST.get('price')
        category_id = request.POST.get('category')
        brand_id = request.POST.get('brand')
        new_images = request.FILES.getlist('images')

        # Size-based stock inputs
        stock_s = request.POST.get('stock_S')
        stock_m = request.POST.get('stock_M')
        stock_l = request.POST.get('stock_L')

        form_data = {
            'name': name,
            'description': description,
            'price': price,
            'stock_S': stock_s,
            'stock_M': stock_m,
            'stock_L': stock_l,
            'category_id': category_id,
            'brand_id': brand_id,
        }

        # Validate product name
        allowed_extensions = ['jpg', 'jpeg', 'png', 'webp']
        if not name:
            errors['name'] = 'Must enter the name'
        elif not re.match(r'^(?=.*[a-zA-Z])[a-zA-Z0-9 _-]+$', name):
            errors['name'] = (
                "Please enter a product name with at least one letter. "
                "Only letters, numbers, spaces, hyphens, and underscores are allowed."
            )
        elif Product.objects.filter(name__iexact=name).exclude(id=product.id).exists():
            errors['name'] = "The product name already exists"

        # Validate price
        try:
            price_val = float(price)
            if price_val <= 0:
                errors['price'] = "Price must be a positive number."
        except (ValueError, TypeError):
            errors['price'] = "Enter a valid number for price."

        # Validate images
        MAX_IMAGES = 3
        if new_images:
            total_images = existing_images.count() + len(new_images)
            if total_images > MAX_IMAGES:
                errors['format'] = f"Total images cannot exceed {MAX_IMAGES}."
            else:
                for image in new_images:
                    ext = image.name.split('.')[-1].lower()
                    if ext not in allowed_extensions:
                        errors['format'] = "Invalid image file format"
                        break
        else:
            # If no new images uploaded, but existing images less than MAX_IMAGES, error
            if existing_images.count() < MAX_IMAGES:
                errors['format'] = f"At least {MAX_IMAGES} images are required."

        # Validate category and brand
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

        # Validate size-based stock values
        if not stock_s or not stock_m or not stock_l:
            errors['stock_sizes'] = "All sizes (S, M, L) must have stock."
        else:
            try:
                s = int(stock_s)
                m = int(stock_m)
                l = int(stock_l)
                if s < 0 or m < 0 or l < 0:
                    errors['stock_sizes'] = "Stock values cannot be negative."
            except ValueError:
                errors['stock_sizes'] = "Stock values must be integers."

        if errors:
            return render(request, 'user_app/edit_product.html', {
                'product': product,
                'categories': categories,
                'brands': brands,
                'errors': errors,
                'form_data': form_data,
                'images': existing_images,
            })

        # Save product and images
        product.name = name
        product.description = description
        product.price = price_val
        product.category = category
        product.brand = brand
        product.stock = s + m + l  # Total stock = sum of sizes
        product.save()

        for image in new_images:
            ProductImage.objects.create(product=product, image=image)

        # Update or create ProductSizeStock entries
        for size, quantity in [('S', s), ('M', m), ('L', l)]:
            ProductSizeStock.objects.update_or_create(
                product=product,
                size=size,
                defaults={'quantity': quantity}
            )

        messages.success(request, "Product updated successfully.")
        return redirect('product_list')

    # GET request - prefill form with existing data
    size_stock = {'S': 0, 'M': 0, 'L': 0}
    for stock in ProductSizeStock.objects.filter(product=product):
        size_stock[stock.size] = stock.quantity

    form_data = {
        'name': product.name,
        'description': product.description,
        'price': product.price,
        'stock_S': size_stock['S'],
        'stock_M': size_stock['M'],
        'stock_L': size_stock['L'],
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
    })

@never_cache
@user_passes_test(lambda x: x.is_superuser, login_url='admin_login')
def toggle_product_status(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product.is_deleted = not product.is_deleted  # Flip status
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

        form_data['name'] = name
        form_data['description'] = description

        # --- Brand Name Validations ---
        if not name:
            errors['name'] = 'Must enter the name.'
        elif not re.match(r'^(?=.*[a-zA-Z])[a-zA-Z0-9 _-]+$', name):
            errors['name'] = (
                "Please enter a brand name with at least one letter. "
                "Only letters, numbers, spaces, hyphens, and underscores are allowed."
            )
        elif Brand.objects.filter(name__iexact=name).exists():
            errors['name'] = "The brand name already exists."

        # --- Logo Validation ---
        if not logo:
            errors['logo'] = "Brand logo is required."
        else:
            ext = logo.name.split('.')[-1].lower()
            if ext not in ['jpg', 'jpeg', 'png', 'webp']:
                errors['logo'] = "Only JPG, JPEG, PNG, or WEBP images are allowed."

        # --- Final Decision ---
        if errors:
            return render(request, 'user_app/add_brand.html', {'errors': errors, 'form_data': form_data})

        # Create and save brand
        Brand.objects.create(
            name=name,
            description=description,
            logo=logo,
            status='active'
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

        # Check for name duplication (only if changed)
        if name.lower() != brand.name.lower():
            if Brand.objects.filter(name__iexact=name).exclude(id=brand.id).exists():
                errors['name'] = "This brand name already exists."

        # Validate logo if uploaded
        if logo:
            ext = logo.name.split('.')[-1].lower()
            if ext not in ['jpg', 'jpeg', 'png', 'webp']:
                errors['logo'] = "Only JPG, JPEG, PNG, or WEBP images are allowed."

        # If there are errors, return the form with previous data
        if errors:
            return render(request, 'user_app/edit_brand.html', {
                'brand': brand,
                'errors': errors,
                'form_data': form_data
            })

        # Check for actual changes before saving
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

    # GET request
    return render(request, 'user_app/edit_brand.html', {'brand': brand})


@never_cache
@user_passes_test(lambda u: u.is_superuser, login_url='admin_login')
def toggle_brand_status(request, brand_id):
    brand = get_object_or_404(Brand, id=brand_id)
    brand.status = 'inactive' if brand.status == 'active' else 'active'
    brand.save()
    return redirect('brand_list')