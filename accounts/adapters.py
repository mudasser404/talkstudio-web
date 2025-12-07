"""
Custom adapters for django-allauth
"""
from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.providers.google.provider import GoogleProvider
from .models import PlatformSettings




class CustomAccountAdapter(DefaultAccountAdapter):
    """
    Custom adapter to customize email context
    """

    def send_confirmation_mail(self, request, emailconfirmation, signup):
        """
        Override to add custom context to confirmation email
        """
        # Get platform settings for welcome bonus info
        settings = PlatformSettings.get_settings()

        # Add free credits and voice clones to context
        ctx = self.get_email_confirmation_url_and_ctx(request, emailconfirmation)
        ctx['free_credits'] = f"{settings.free_trial_credits:,}"
        ctx['free_voice_clones'] = settings.free_trial_voice_clones

        # Send the email
        self.send_mail('account/email/email_confirmation_signup', emailconfirmation.email_address.email, ctx)

    def get_email_confirmation_url_and_ctx(self, request, emailconfirmation):
        """
        Get the URL and context for email confirmation
        """
        ctx = {}
        ctx["user"] = emailconfirmation.email_address.user
        ctx["activate_url"] = self.get_email_confirmation_url(request, emailconfirmation)
        ctx["current_site"] = request.get_host() if request else 'Talk Studio Platform'
        ctx["key"] = emailconfirmation.key

        # Add platform settings
        settings = PlatformSettings.get_settings()
        ctx['free_credits'] = f"{settings.free_trial_credits:,}"
        ctx['free_voice_clones'] = settings.free_trial_voice_clones

        return ctx


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Custom adapter to load OAuth credentials from database
    """

    def get_app(self, request, provider, client_id=None):
        """
        Override to dynamically load Google OAuth credentials from database
        """
        if provider == 'google' or isinstance(provider, GoogleProvider):
            settings = PlatformSettings.get_settings()

            # If Google OAuth is enabled and configured, create a SocialApp instance
            if settings.google_login_enabled and settings.google_client_id and settings.google_client_secret:
                from allauth.socialaccount.models import SocialApp
                from django.contrib.sites.models import Site

                # Check if SocialApp exists in database
                try:
                    app = SocialApp.objects.get(provider='google')
                    # Update credentials if changed
                    app.client_id = settings.google_client_id
                    app.secret = settings.google_client_secret
                    app.save()
                except SocialApp.DoesNotExist:
                    # Create new SocialApp
                    app = SocialApp.objects.create(
                        provider='google',
                        name='Google OAuth',
                        client_id=settings.google_client_id,
                        secret=settings.google_client_secret,
                    )
                    # Add current site
                    app.sites.add(Site.objects.get_current())

                return app

        # Fall back to default behavior for other providers
        return super().get_app(request, provider, client_id)

    def is_auto_signup_allowed(self, request, sociallogin):
        """
        Allow automatic signup for social accounts
        """
        return True

    def populate_user(self, request, sociallogin, data):
        """
        Populate user instance with data from social provider
        """
        user = super().populate_user(request, sociallogin, data)

        # Extract additional data from Google
        if sociallogin.account.provider == 'google':
            user.first_name = data.get('given_name', '')
            user.last_name = data.get('family_name', '')

        return user
