from django import forms
from django.contrib.auth.forms import UserCreationForm
from user_app.models import CustomUser,Product

class UserSignupForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'password1', 'password2')

class ProductForm(forms.ModelForm):
    class Meta:
        model=Product
        fields=['name','description','price','stock','category','brand']