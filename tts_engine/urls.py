"""
URL Configuration for TTS Engine
"""

from django.urls import path
from . import views

app_name = 'tts_engine'

urlpatterns = [
    # Main studio page
    path('studio/', views.index_tts_studio, name='studio'),

    # API endpoints
    path('generate/', views.generate_speech, name='generate_speech'),
    path('api/analyze-emotion/', views.analyze_emotion, name='analyze_emotion'),
    path('api/model-info/', views.get_model_info, name='model_info'),

    # Download endpoint
    path('download/<str:filename>/', views.download_audio, name='download_audio'),

    # Progress tracking
    path('api/progress/<str:task_id>/', views.check_progress, name='check_progress'),
    path('api/generation-progress/<str:task_id>/', views.get_generation_progress, name='generation_progress'),
]
