from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from .models import CustomUser
from user_app.forms import LoginForm
import random
import time
from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse
from django.contrib.auth.tokens import PasswordResetTokenGenerator  # For generating reset tokens
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode  # For encoding/decoding user ID
from django.utils.encoding import force_bytes, force_str


OTP_EXPIRY_SECONDS = 600  # OTP expires after 10 minutes (optional enhancement)


@never_cache
def signup_view(request):
    if request.user.is_authenticated:
        return redirect('user_dashboard')
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip().lower()  # Normalize email
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')

        errors = {}

        if not username:
            errors['username'] = "Username is required."
        elif CustomUser.objects.filter(username=username).exists():
            errors['username'] = "Username already taken."

        if not email:
            errors['email'] = "Email is required."
        elif not email.endswith('@gmail.com'):
            errors['email'] = 'Enter a valid Gmail address.'
        elif CustomUser.objects.filter(email=email).exists():
            errors['email'] = "Email already in use."

        if not password1:
            errors['password1'] = "Password is required."
        elif password1 != password2:
            errors['password2'] = "Passwords do not match."
        elif len(password1) < 6:
            errors['password1'] = "Password must be at least 6 characters."

        if errors:
            return render(request, 'user_app/signup.html', {'errors': errors})

        # Generate OTP and save signup data + timestamp in session
        otp = random.randint(100000, 999999)
        request.session['signup_data'] = {
            'username': username,
            'email': email,
            'password': password1,
            'otp': str(otp),
            'otp_created_at': time.time()
        }

        # Send OTP email
        send_mail(
            'Your ShopKickora OTP',
            f'Your OTP for ShopKickora signup is: {otp}',
            settings.EMAIL_HOST_USER,
            [email],
            fail_silently=False,
        )

        return redirect('verify_otp')

    return render(request, 'user_app/signup.html')


@never_cache
def verify_otp_view(request):
    if request.user.is_authenticated:
        return redirect('user_dashboard')
    signup_data = request.session.get('signup_data')
    if not signup_data:
        return redirect('signup')  # Prevent direct access without signup

    if request.method == 'POST':
        entered_otp = request.POST.get('otp', '').strip()

        # Validate OTP format
        if len(entered_otp) != 6 or not entered_otp.isdigit():
            messages.error(request, "Enter a valid 6-digit OTP.")
            return render(request, 'user_app/verify_otp.html')

        # Check if OTP expired
        otp_created_at = signup_data.get('otp_created_at', 0)
        if time.time() - otp_created_at > OTP_EXPIRY_SECONDS:
            messages.error(request, "OTP expired. Please resend and try again.")
            return render(request, 'user_app/verify_otp.html')

        if entered_otp == signup_data['otp']:
            # Create user and login
            user = CustomUser.objects.create_user(
                username=signup_data['username'],
                email=signup_data['email'],
                password=signup_data['password']
            )
            user.backend = 'django.contrib.auth.backends.ModelBackend'
            login(request, user)
            request.session.pop('signup_data', None)
            messages.success(request, "Account created successfully!")
            return redirect('user_dashboard')
        else:
            messages.error(request, "Invalid OTP. Please try again.")

    return render(request, 'user_app/verify_otp.html')


@never_cache
def resend_otp(request):
    signup_data = request.session.get('signup_data')
    if signup_data:
        otp = random.randint(100000, 999999)
        signup_data['otp'] = str(otp)
        signup_data['otp_created_at'] = time.time()
        request.session['signup_data'] = signup_data

        send_mail(
            'Your ShopKickora OTP (Resend)',
            f'Your new OTP is: {otp}',
            'noreply@shopkickora.com',
            [signup_data['email']],
            fail_silently=False,
        )

        messages.success(request, "A new OTP has been sent to your email.")
    else:
        messages.error(request, "Session expired or invalid. Please signup again.")
        return redirect('signup')

    return redirect('verify_otp')

@never_cache
def forgot_password_view(request):
    if request.method == "POST":
        email = request.POST.get('email', '').strip().lower()
        if not email:
            messages.error(request, "Email is required.")
            return render(request, 'user_app/forgot_password.html')

        try:
            user = CustomUser.objects.get(email=email)
            # Generate a token for password reset
            token_generator = PasswordResetTokenGenerator()
            token = token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))

            # Create reset URL
            reset_url = request.build_absolute_uri(
                reverse('reset_password', kwargs={'uidb64': uid, 'token': token})
            )

            # Send password reset email
            send_mail(
                'ShopKickora Password Reset',
                f'Click the link to reset your password: {reset_url}',
                'noreply@shopkickora.com',
                [email],
                fail_silently=False,
            )

            messages.success(request, "A password reset link has been sent to your email.")
            return redirect('login')
        except CustomUser.DoesNotExist:
            messages.error(request, "No user found with this email address.")
            return render(request, 'user_app/forgot_password.html')

    return render(request, 'user_app/forgot_password.html')

@never_cache
def reset_password_view(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = CustomUser.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
        user = None

    token_generator = PasswordResetTokenGenerator()
    if user is not None and token_generator.check_token(user, token):
        if request.method == "POST":
            password1 = request.POST.get('password1', '')
            password2 = request.POST.get('password2', '')

            errors = {}
            if not password1:
                errors['password1'] = "Password is required."
            elif password1 != password2:
                errors['password2'] = "Passwords do not match."
            elif len(password1) < 6:
                errors['password1'] = "Password must be at least 6 characters."

            if errors:
                return render(request, 'user_app/reset_password.html', {'errors': errors, 'uidb64': uidb64, 'token': token})

            # Update the user's password
            user.set_password(password1)
            user.save()
            messages.success(request, "Password reset successfully. Please log in with your new password.")
            return redirect('login')

        return render(request, 'user_app/reset_password.html', {'uidb64': uidb64, 'token': token})
    else:
        messages.error(request, "Invalid or expired reset link.")
        return redirect('forgot_password')

@never_cache
def login_view(request):
    if request.user.is_authenticated:
        return redirect('user_dashboard')


    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                if user.is_blocked:
                    messages.error(request, "Your account is currently suspended.")
                else:
                    login(request, user)
                    return redirect('user_dashboard')
            else:
                form.add_error(None, "Invalid username or password.")
    else:
        form = LoginForm()

    return render(request, 'user_app/login.html', {'form': form})


@never_cache
@login_required(login_url='login')
def user_dashboard(request):
    if request.user.is_superuser:
        return redirect('admin_dashboard')
    return render(request, 'user_app/dashboard.html')


@never_cache
def logout_view(request):
    logout(request)
    request.session.flush()
    list(messages.get_messages(request))
    return redirect('login')
