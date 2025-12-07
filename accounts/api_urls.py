"""
URL configuration for API key management
"""
from django.urls import path
from . import api_views

urlpatterns = [
    # API Key Management (requires login)
    path('generate/', api_views.generate_api_key, name='api-key-generate'),
    path('list/', api_views.list_api_keys, name='api-key-list'),
    path('<int:key_id>/delete/', api_views.delete_api_key, name='api-key-delete'),
]
