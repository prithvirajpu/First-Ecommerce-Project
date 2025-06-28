from django import forms
from user_app.models import ProductOffer, CategoryOffer,Product
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
            'products': forms.SelectMultiple(attrs={'class': 'form-select', 'size': '6'}),
            'start_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'end_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # ✅ Filter only non-deleted products
        self.fields['products'].queryset = Product.objects.filter(is_deleted=False)


    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('start_date')
        end = cleaned_data.get('end_date')
        if start and end and start >= end:
            raise forms.ValidationError('Start date must be before end date.')
        return cleaned_data
    
class CategoryOfferForm(forms.ModelForm):
    class Meta:
        model=CategoryOffer
        fields=['category','discount_percentage','start_date','end_date','is_active']
        widgets = {
            'start_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'end_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    def clean(self):
        cleaned_data=super().clean()
        start=cleaned_data.get('start_date')
        end=cleaned_data.get('end_date')
        if start and end and start>=end:
            raise forms.ValidationError('Start date must be before end date.')
        return cleaned_data