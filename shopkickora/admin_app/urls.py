from django.urls import path
from . import views

urlpatterns = [
    path('users/', views.user_list, name='user_list'),
    path('users/block/<int:user_id>/', views.block_user, name='admin_block_user'),
    path('users/unblock/<int:user_id>/', views.unblock_user, name='admin_unblock_user'),
    path('', views.admin_login, name='admin_login'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-logout/', views.admin_logout, name='admin_logout'),
    path('categories/', views.category_list, name='category_list'),
    path('categories/edit/<int:category_id>/', views.edit_category, name='edit_category'),
    path('catrgories/toggle/<int:category_id>/',views.toggle_category_status,name='toggle_category_status'),
    path('categories/add/', views.add_category, name='add_category'),
    path('brands/', views.brand_list, name='brand_list'),     
    path('products/', views.product_list, name='product_list'),
    path('products/edit/<int:product_id>/', views.edit_product, name='edit_product'),
    path('products/toggle/<int:product_id>/', views.toggle_product_status, name='toggle_product_status'), 
    path('products/add/', views.add_product, name='add_product'),
    path('brands/add/', views.add_brand, name='add_brand'),
    path('brands/edit/<int:brand_id>/', views.edit_brand, name='edit_brand'),
    path('brands/toggle/<int:brand_id>/', views.toggle_brand_status, name='toggle_brand_status'), 
    path('orders/', views.admin_order_list, name='admin_order_list'),
    path('orders/<int:order_id>/', views.admin_order_detail, name='admin_order_detail'),
    path('orders/update-status/<int:order_id>/', views.admin_update_order_status, name='admin_update_order_status'),
    path('orders/return/approve/<int:order_item_id>/', views.approve_return, name='admin_approve_return'),
    path('myadmin/orders/reject-return/<int:order_item_id>/', views.reject_return, name='admin_reject_return'),
    path('offers/',views.list_offers,name='list_offers'),
    path('offers/add-product/',views.add_product_offer,name='add_product_offer'),
    path('offers/add-category/',views.add_category_offer,name='add_category_offer'),
    path('offers/edit-product/<int:offer_id>/', views.edit_product_offer, name='edit_product_offer'),
    path('offers/edit-category/<int:offer_id>/', views.edit_category_offer, name='edit_category_offer'),

]

