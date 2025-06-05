from django.db import IntegrityError
from django.shortcuts import render, redirect,get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .forms import AdminLoginForm
from django.core.paginator import Paginator
from django.db.models import Q
from user_app.models import CustomUser,Brand,ProductImage,Product,Category
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

@user_passes_test(lambda u: u.is_superuser, login_url='admin_login')
def block_user(request,user_id):
    user=get_object_or_404(CustomUser,id=user_id)
    user.is_blocked=True
    user.save()
    messages.success(request,f"{user.username} has been blocked.")
    return redirect('user_list')

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


@user_passes_test(lambda u: u.is_superuser, login_url='admin_login')
def edit_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    if request.method == 'POST':
        category.name = request.POST.get('name').strip()
        category.description = request.POST.get('description').strip()
        if Category.objects.filter(name__iexact=category.name).exclude(id=category.id).exists():
            messages.error(request, "A category with this name already exists!")
            return render(request, 'admin_app/edit_category.html', {'category': category})

        category.save()
        messages.success(request, "Category updated successfully!")
        return redirect('category_list')
    return render(request, 'admin_app/edit_category.html', {'category': category})



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
    products = Product.objects.filter(is_deleted=False).order_by('-created_at')  # Latest first

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

@user_passes_test(lambda u: u.is_superuser, login_url='admin_login')
def add_product(request):
    categories = Category.objects.filter(is_deleted=False)
    brands = Brand.objects.filter(status='active')
    errors={}
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        price = request.POST.get('price')
        stock = request.POST.get('stock')
        category_id = request.POST.get('category')
        brand_id = request.POST.get('brand')
        images = request.FILES.getlist('images')

        if len(images) < 3:
            errors['format']="Please upload at least 3 images."
        allowed_extensions = ['jpg', 'jpeg', 'png', 'webp']

        # Validate each image extension
        for image in images:
            ext = image.name.split('.')[-1].lower()
            if ext not in allowed_extensions:
                errors['format']="Invalid file format"
        try:
            category = Category.objects.get(id=category_id)
            brand = Brand.objects.get(id=brand_id)
        except Category.DoesNotExist:
            messages.error(request, "Invalid category or brand.")

        if errors:
            context = {
                'categories': categories,
                'brands': brands,
                'errors': errors,
                'form_data': {
                    'name': name,
                    'description': description,
                    'price': price,
                    'stock': stock,
                    'category_id': category_id,
                    'brand_id': brand_id,
                }
            }
            return render(request, 'user_app/add_product.html', context)
        product = Product.objects.create(
                name=name,
                description=description,
                price=price,
                stock=stock,
                category=category,
                brand=brand
            )

        for image in images:
            ProductImage.objects.create(product=product, image=image)

        messages.success(request, "Product added successfully.")
        return redirect('product_list')

    context = {
        'categories': categories,
        'brands': brands,
        'errors':errors
    }
    return render(request, 'user_app/add_product.html', context)

@user_passes_test(lambda u: u.is_superuser, login_url='admin_login')
def edit_product(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_deleted=False)
    categories = Category.objects.filter(is_deleted=False)
    brands = Brand.objects.all()
    existing_images = ProductImage.objects.filter(product=product)

    if request.method == 'POST':
        product.name = request.POST.get('name')
        product.description = request.POST.get('description')
        product.price = request.POST.get('price')
        product.stock = request.POST.get('stock')
        product.category_id = request.POST.get('category')
        product.brand_id = request.POST.get('brand')
        product.save()

        new_images = request.FILES.getlist('images')
        if new_images:
            total_images = existing_images.count() + len(new_images)
            if total_images < 3:
                messages.error(request, "Total images (existing + new) must be at least 3.")
                return redirect('edit_product', product_id=product.id)

            for image in new_images:
                ProductImage.objects.create(product=product, image=image)

        messages.success(request, "Product updated successfully.")
        return redirect('product_list')

    context = {
        'product': product,
        'categories': categories,
        'brands': brands,
        'images': existing_images
    }
    return render(request, 'user_app/edit_product.html', context)

@user_passes_test(lambda x:x.is_superuser,login_url='admin_login')
def toggle_product_status(request,product_id):
    product=get_object_or_404(Product,id=product_id)
    product.is_deleted=not product.is_deleted
    product.save()
    status= "enabled" if product.is_deleted else "disabled"
    messages.success(request,f"product {status} successfully")
    return redirect('product_list')

@never_cache
@user_passes_test(lambda u: u.is_superuser, login_url='admin_login')
def brand_list(request):
    brands=Brand.objects.all().order_by('-created_at')
    context={'brands':brands}
    return render(request,'user_app/brand_list.html',context)


@user_passes_test(lambda u: u.is_superuser, login_url='admin_login')
def add_brand(request):
    errors = {}
    form_data = {}

    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        logo = request.FILES.get('logo')

        form_data['name'] = name
        form_data['description'] = description

        if not name:
            errors['name'] = 'Must enter the name'
        elif not re.match(r'^(?=.*[a-zA-Z])[a-zA-Z0-9 _-]+$', name):
            errors['name'] = "Brand name must contain at least one letter and only use letters, numbers, spaces, hyphens, or underscores."
        elif Brand.objects.filter(name__iexact=name).exists():
            errors['name'] = "The brand name already exists"

        if not logo:
            errors['logo'] = "Brand logo is required."
        else:
            ext = logo.name.split('.')[-1].lower()
            if ext not in ['jpg', 'jpeg', 'png', 'webp']:
                errors['logo'] = "Only JPG, JPEG, PNG, or WEBP images are allowed."

        if errors:
            return render(request, 'user_app/add_brand.html', {'errors': errors, 'form_data': form_data})

        Brand.objects.create(name=name, description=description, logo=logo, status='active')
        messages.success(request, "Brand created successfully.")
        return redirect('brand_list')

    return render(request, 'user_app/add_brand.html', {'errors': {}, 'form_data': {}})

# @user_passes_test(lambda u: u.is_superuser, login_url='admin_login')
# def add_brand(request):
#     errors = {}
#     form_data = {}

#     if request.method == 'POST':
#         name = request.POST.get('name')
#         description = request.POST.get('description')
#         logo = request.FILES.get('logo')

#         # Save form data to repopulate in case of errors
#         form_data = {
#             'name': name,
#             'description': description,
#         }

#         # Validation checks
#         if not name:
#             errors['name'] = 'Brand name is required.'
#         elif not re.match(r'^(?=.*[a-zA-Z])[a-zA-Z0-9 _-]+$', name):
#             errors['name'] = "Brand name must contain at least one letter and only use letters, numbers, spaces, hyphens, or underscores."
#         elif Brand.objects.filter(name__iexact=name).exists():
#             errors['name'] = "This brand name already exists."

#         if not logo:
#             errors['logo'] = "Brand logo is required."
#         else:
#             allowed_extensions = ['jpg', 'jpeg', 'png', 'webp']
#             ext = logo.name.split('.')[-1].lower()
#             if ext not in allowed_extensions:
#                 errors['logo'] = "Logo must be in JPG, JPEG, PNG, or WEBP format."

#         # If there are errors, return to form
#         if errors:
#             return render(request, 'user_app/add_brand.html', {
#                 'errors': errors,
#                 'form_data': form_data
#             })

#         # Save brand
#         Brand.objects.create(
#             name=name,
#             description=description,
#             logo=logo,
#             status='active'
#         )
#         messages.success(request, "Brand created successfully.")
#         return redirect('brand_list')

#     return render(request, 'user_app/add_brand.html')

# @user_passes_test(lambda u: u.is_superuser, login_url='admin_login')
# def add_brand(request):
#     errors={}
#     if request.method == 'POST':
#         name = request.POST.get('name')
#         description = request.POST.get('description')
#         logo = request.FILES.get('logo')  

#         if not name:
#             errors['name']='Must enter the name'
#         elif not re.match(r'^(?=.*[a-zA-Z])[a-zA-Z0-9 _-]+$', name):
#             errors['name']="Brand name must contain at least one letter and only use letters, numbers, spaces, hyphens, or underscores."
#         elif Brand.objects.filter(name__iexact=name).exists():
#             errors['name']="The brand name already exists"
#         if not logo:
#             errors['logo'] = "Brand logo is required."
#         if errors:
#             return render(request,'user_app/add_brand.html',{'errors':errors})
#         if not errors:
#             Brand.objects.create(name=name,description=description,logo=logo,status='active',)
#             messages.success(request, "Brand created successfully.") 
#             return redirect('brand_list')

#     return render(request, 'user_app/add_brand.html')

@user_passes_test(lambda u: u.is_superuser, login_url='admin_login')
def edit_brand(request, brand_id):
    brand = get_object_or_404(Brand, id=brand_id)
    if request.method == 'POST':
        brand.name = request.POST.get('name')
        brand.description = request.POST.get('description')
        if Brand.objects.filter(name__iexact=brand.name).exclude(id=brand_id).exists():
            messages.error(request,"This brand name is already exist")
            return render(request, 'user_app/edit_brand.html', {'brand': brand})
        if 'logo' in request.FILES:
            brand.logo = request.FILES['logo']
        brand.save()
        messages.success(request, "Brand updated successfully.")
        return redirect('brand_list')
    return render(request, 'user_app/edit_brand.html', {'brand': brand})

@user_passes_test(lambda u: u.is_superuser, login_url='admin_login')
def toggle_brand_status(request, brand_id):
    brand = get_object_or_404(Brand, id=brand_id)
    brand.status = 'inactive' if brand.status == 'active' else 'active'
    brand.save()
    return redirect('brand_list')