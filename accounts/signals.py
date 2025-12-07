"""
Signal handlers for user authentication events
"""
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()


@receiver(user_logged_in)
def user_logged_in_handler(sender, request, user, **kwargs):
    """
    Update user's last_login when they log in
    """
    # Django already updates last_login, but we can add logging here
    from .models import ActivityLog

    # Log the login activity
    ActivityLog.log_activity(
        action='user_login',
        admin_user=user,
        description=f'User {user.email} logged in',
        severity='low',
        metadata={'login_time': timezone.now().isoformat()},
        request=request
    )


@receiver(user_logged_out)
def user_logged_out_handler(sender, request, user, **kwargs):
    """
    Handle user logout
    Note: We don't clear last_login, we just let it age out
    Users become "offline" after 15 minutes of inactivity automatically
    """
    if user:
        from .models import ActivityLog

        # Log the logout activity
        ActivityLog.log_activity(
            action='user_logout',
            admin_user=user,
            description=f'User {user.email} logged out',
            severity='low',
            metadata={'logout_time': timezone.now().isoformat()},
            request=request
        )
