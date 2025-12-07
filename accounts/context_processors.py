"""
Context processors for accounts app
Provides platform settings to all templates
"""
from .models import PlatformSettings


def platform_settings(request):
    """
    Make platform settings available in all templates
    """
    settings = PlatformSettings.get_settings()

    return {
        'google_oauth_enabled': settings.google_login_enabled and settings.google_client_id and settings.google_client_secret,
        'platform_settings': settings,
    }
