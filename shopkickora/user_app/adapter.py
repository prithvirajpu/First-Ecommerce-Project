from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.account.adapter import DefaultAccountAdapter


class CustomGoogleOAuth2Adapter(GoogleOAuth2Adapter):
    def get_auth_params(self, request, action):
        params = super().get_auth_params(request, action)
        if not request.session.get('google_login_attempted'):
            params['prompt'] = 'select_account'
            request.session['google_login_attempted'] = True
        return params

class CustomAccountAdapter(DefaultAccountAdapter):
    def populate_username(self, request, user):
        user.username = user.email
