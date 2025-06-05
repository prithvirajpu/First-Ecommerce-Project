import re
from django import forms
from django.contrib.auth.forms import UserCreationForm
from user_app.models import CustomUser,Product

class UserSignupForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'password1', 'password2')

class LoginForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username',
            'autofocus': True,
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password',
        })
    )
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if not re.match(r'^(?=.*[a-zA-Z])[a-zA-Z0-9 _-]+$', username):
            raise forms.ValidationError(
                "Name must contain at least one letter and only use letters, numbers, spaces, hyphens, or underscores."
            )
        return username

class ProductForm(forms.ModelForm):
    class Meta:
        model=Product
        fields=['name','description','price','stock','category','brand']