from django.shortcuts import render, redirect,get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .forms import AdminLoginForm
from django.core.paginator import Paginator
from django.db.models import Q
from user_app.models import CustomUser,Brand,ProductImage,Product,Category
from django.contrib.auth.decorators import user_passes_test
from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import login_required



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

def block_user(request,user_id):
    user=get_object_or_404(CustomUser,id=user_id)
    user.is_blocked=True
    user.save()
    messages.success(request,f"{user.username} has been blocked.")
    return redirect('user_list')

def unblock_user(request,user_id):
    user=get_object_or_404(CustomUser,id=user_id)
    user.is_blocked=False
    user.save()
    messages.success(request,f"{user.username} has been unblocked.")
    return redirect('user_list')

@never_cache
@user_passes_test(lambda u: u.is_superuser, login_url='admin_login')
def category_list(request):
    query = request.GET.get('q', '')
    categories = Category.objects.filter(is_deleted=False).order_by('-created_at')

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


@user_passes_test(lambda u: u.is_superuser, login_url='admin_login')
def add_category(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        Category.objects.create(name=name, description=description)
        messages.success(request, "Category added successfully!")
        return redirect('category_list')
    return render(request, 'admin_app/add_category.html')


@user_passes_test(lambda u: u.is_superuser, login_url='admin_login')
def edit_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    if request.method == 'POST':
        category.name = request.POST.get('name')
        category.description = request.POST.get('description')
        category.save()
        messages.success(request, "Category updated successfully!")
        return redirect('category_list')
    return render(request, 'admin_app/edit_category.html', {'category': category})


@user_passes_test(lambda u: u.is_superuser, login_url='admin_login')
def delete_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    category.is_deleted = True
    category.save()
    messages.success(request, "Category deleted successfully!")
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


def add_product(request):
    categories = Category.objects.filter(is_deleted=False)
    brands = Brand.objects.all()

    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        price = request.POST.get('price')
        stock = request.POST.get('stock')
        category_id = request.POST.get('category')
        brand_id = request.POST.get('brand')
        images = request.FILES.getlist('images')

        if len(images) < 3:
            messages.error(request, "Please upload at least 3 images.")
            return redirect('add_product')

        try:
            category = Category.objects.get(id=category_id)
            brand = Brand.objects.get(id=brand_id)
        except (Category.DoesNotExist, Brand.DoesNotExist):
            messages.error(request, "Invalid category or brand.")
            return redirect('add_product')

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
        'brands': brands
    }
    return render(request, 'user_app/add_product.html', context)
