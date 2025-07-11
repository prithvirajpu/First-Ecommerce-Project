from django import forms
from user_app.models import Category, ProductOffer, CategoryOffer,Product
from django.utils import timezone

class AdminLoginForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter username'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter password'})
    )

class ProductOfferForm(forms.ModelForm):
    class Meta:
        model = ProductOffer
        fields = ['name', 'products', 'discount_percentage', 'start_date', 'end_date', 'is_active']
        widgets = {
            'products': forms.CheckboxSelectMultiple(),
            'start_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'end_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        all_products = Product.objects.filter(
            is_deleted=False,
            category__is_deleted=False,
            category__is_active=True,
            brand__is_active=True
        )

        # Retain selected products in edit view
        selected_products = self.instance.products.all() if self.instance.pk else Product.objects.none()
        unselected_products = all_products.exclude(pk__in=selected_products)

        # Store for template access if needed
        self.selected_products = selected_products
        self.unselected_products = unselected_products

        # Set filtered queryset
        self.fields['products'].queryset = all_products | selected_products  # to avoid removing selected deleted ones
        self.fields['products'].required = False

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('start_date')
        end = cleaned_data.get('end_date')
        products = cleaned_data.get('products')

        if start and end and start >= end:
            self.add_error('start_date', "Start date must be before end date.")
        if not products or len(products) == 0:
            self.add_error('products', "Please select at least one product.")

        return cleaned_data


    
class CategoryOfferForm(forms.ModelForm):
    class Meta:
        model = CategoryOffer
        fields = ['categories', 'discount_percentage', 'start_date', 'end_date', 'is_active']
        widgets = {
            'categories': forms.CheckboxSelectMultiple(),
            'start_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'end_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['categories'].queryset = Category.objects.filter(is_deleted=False, is_active=True)
        self.fields['categories'].required = False

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('start_date')
        end = cleaned_data.get('end_date')
        categories = cleaned_data.get('categories')

        if start and end and start >= end:
            self.add_error('start_date', "Start date must be before end date.")
        if not categories or categories.count() == 0:
            self.add_error('categories', "Please select at least one category.")

        return cleaned_data
