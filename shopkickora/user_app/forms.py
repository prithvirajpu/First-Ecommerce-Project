from django import forms
from django.contrib.auth.forms import UserCreationForm
from user_app.models import CustomUser

class UserSignupForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'password1', 'password2')
