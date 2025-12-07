"""
Middleware to track user activity for online/offline status
"""
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()


class UserActivityMiddleware:
    """
    Middleware to update user's last_login on every request
    This allows us to track who is currently online
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Update last_login for authenticated users on every request
        if request.user.is_authenticated:
            # Update last_login to current time
            User.objects.filter(pk=request.user.pk).update(last_login=timezone.now())

        response = self.get_response(request)
        return response
