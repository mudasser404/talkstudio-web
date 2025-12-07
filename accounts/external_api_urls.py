"""
URL configuration for external API endpoints (authenticated via API key)
"""
from django.urls import path
from . import api_views

urlpatterns = [
    # TTS API Endpoints (require API key authentication)
    path('generate/', api_views.api_generate_voice, name='api-tts-generate'),

    # Voice Management API
    path('list/', api_views.api_list_voices, name='api-voices-list'),
    path('clone/', api_views.api_clone_voice, name='api-voices-clone'),
]
