import re
from django import forms
from django.contrib.auth.forms import UserCreationForm
from user_app.models import CustomUser,Product
from .models import CustomUser

class ProfileImageForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['profile_image']
    
    def clean_profile_image(self):
        ALLOWED_CONTENT_TYPES = [
            'image/jpeg',
            'image/png',
            'image/gif',
            'image/webp',
            'image/svg+xml',
            ]

        ALLOWED_EXTENSIONS = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg']

        image = self.cleaned_data.get('profile_image')
        if image:
            if hasattr(image, 'content_type'):
                if image.content_type not in ALLOWED_CONTENT_TYPES:
                    raise forms.ValidationError("Unsupported image type. Please upload JPG, PNG, GIF, SVG, or WEBP files.")
            else:
                raise forms.ValidationError("Cannot determine the file type.")
            
            ext = image.name.split('.')[-1].lower()
            if ext not in ALLOWED_EXTENSIONS:
                raise forms.ValidationError("Unsupported file extension.")
            
            if image.size > 2 * 1024 * 1024:
                raise forms.ValidationError("Image file too large ( > 2MB ).")
        return image


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
        
class UserSignupForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'password1', 'password2')

