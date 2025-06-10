# user_app/signals.py
from django.dispatch import receiver
from allauth.account.signals import user_logged_in, user_signed_up
from allauth.socialaccount.models import SocialAccount
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib.auth import logout

# It's better to block *before* they are fully logged in if possible,
# but `user_logged_in` is a good general catch-all.
# For more granular control, check allauth's adapters.

@receiver(user_logged_in)
def block_google_user_on_login(sender, request, user, **kwargs):
    # Check if the user logged in via a social account
    social_accounts = SocialAccount.objects.filter(user=user)
    for account in social_accounts:
        if account.provider == 'google':
            # Block the user if they logged in via Google
            user.is_blocked = True
            user.save()
            # Log them out immediately if they were just logged in
            logout(request)
            messages.error(request, "Google login is not allowed. Your account has been blocked.")
            # Redirect to login page or a custom blocked page
            return redirect(reverse('login')) # Make sure 'login' is your login URL name

# If you also want to prevent *new* Google sign-ups, you can use user_signed_up
# This is more restrictive as it blocks them at registration.
@receiver(user_signed_up)
def block_google_user_on_signup(sender, request, user, **kwargs):
    social_account = SocialAccount.objects.filter(user=user).first()
    if social_account and social_account.provider == 'google':
        user.is_blocked = True
        user.save()
        # Optionally, you might want to de-activate the social account
        # social_account.delete() # Or just don't allow them to proceed
        messages.error(request, "Google sign-up is not permitted. Your account has been blocked.")
        logout(request) # Log out if somehow they got partially logged in
        return redirect(reverse('login'))