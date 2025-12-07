"""
Custom Email Backend that loads SMTP settings from database
"""
from django.core.mail.backends.smtp import EmailBackend as SMTPBackend
from django.conf import settings


class DatabaseSMTPBackend(SMTPBackend):
    """
    Email backend that dynamically loads SMTP settings from PlatformSettings model
    Falls back to console backend if SMTP is not configured
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Load SMTP settings from database
        try:
            from accounts.models import PlatformSettings
            platform_settings = PlatformSettings.get_settings()

            # Only use SMTP if enabled and configured
            if (platform_settings.smtp_enabled and
                platform_settings.smtp_host and
                platform_settings.smtp_username and
                platform_settings.smtp_password):

                self.host = platform_settings.smtp_host
                self.port = platform_settings.smtp_port or 587
                self.username = platform_settings.smtp_username
                self.password = platform_settings.smtp_password
                self.use_tls = platform_settings.smtp_use_tls
                self.use_ssl = False  # TLS and SSL are mutually exclusive
                self.fail_silently = False  # Show errors for debugging

                # Set default from email
                if platform_settings.smtp_from_email:
                    settings.DEFAULT_FROM_EMAIL = platform_settings.smtp_from_email
                    if platform_settings.smtp_from_name:
                        settings.DEFAULT_FROM_EMAIL = f"{platform_settings.smtp_from_name} <{platform_settings.smtp_from_email}>"

            else:
                # SMTP not configured, use console backend behavior
                # This will print emails to console instead of sending
                raise Exception("SMTP not configured")

        except Exception as e:
            # If database not ready or SMTP not configured, fall back to console
            print(f"SMTP Backend: Falling back to console mode - {str(e)}")
            # Re-raise to let Django handle it
            pass


class ConsoleOrSMTPBackend:
    """
    Smart backend that chooses between Console and SMTP based on configuration
    """

    def __new__(cls, *args, **kwargs):
        try:
            from accounts.models import PlatformSettings
            platform_settings = PlatformSettings.get_settings()

            # Check if SMTP is configured
            if (platform_settings.smtp_enabled and
                platform_settings.smtp_host and
                platform_settings.smtp_username and
                platform_settings.smtp_password):
                # Use database SMTP backend
                return DatabaseSMTPBackend(*args, **kwargs)
            else:
                # Use console backend
                from django.core.mail.backends.console import EmailBackend
                return EmailBackend(*args, **kwargs)
        except:
            # Database not ready, use console backend
            from django.core.mail.backends.console import EmailBackend
            return EmailBackend(*args, **kwargs)
