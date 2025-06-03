from django.urls import path
from . import views

urlpatterns = [
    path('users/', views.user_list, name='user_list'),
    path('users/block/<int:user_id>/', views.block_user, name='admin_block_user'),
    path('users/unblock/<int:user_id>/', views.unblock_user, name='admin_unblock_user'),
    path('', views.admin_login, name='admin_login'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-logout/', views.admin_logout, name='admin_logout'),
    path('categories/',views.category_list,name='category_list'),
    path('products/', views.product_list, name='product_list'),
    # path('products/add/', views.add_product, name='add_product'),
    # path('products/edit/<int:product_id>/', views.edit_product, name='edit_product'),
    # path('products/delete/<int:product_id>/', views.delete_product, name='delete_product'),
]

