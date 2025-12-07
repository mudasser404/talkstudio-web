from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    VoiceLibraryViewSet,
    ClonedVoiceViewSet,
    GeneratedAudioViewSet,
    VoiceGenerationHistoryViewSet,
    DefaultVoiceManagementViewSet,
    generate_audio_from_gradio,
    get_user_credit_info,
    get_current_user_info,
    get_gradio_access_token,
    open_gradio_ui,
    save_reference_voice,
    get_saved_voices,
    get_saved_voice_details
)

router = DefaultRouter()
router.register(r'library', VoiceLibraryViewSet, basename='voice-library')
router.register(r'cloned', ClonedVoiceViewSet, basename='cloned-voice')
router.register(r'generated', GeneratedAudioViewSet, basename='generated-audio')
router.register(r'history', VoiceGenerationHistoryViewSet, basename='generation-history')
router.register(r'default-voices', DefaultVoiceManagementViewSet, basename='default-voices')

app_name = 'voices'

urlpatterns = [
    path('', include(router.urls)),
    path('generate-from-gradio/', generate_audio_from_gradio, name='generate-from-gradio'),
    path('credit-info/', get_user_credit_info, name='credit-info'),
    path('current-user/', get_current_user_info, name='current-user'),
    path('gradio-token/', get_gradio_access_token, name='gradio-token'),
    path('open-gradio/', open_gradio_ui, name='open-gradio'),
    # Save voice feature
    path('save-voice/', save_reference_voice, name='save-voice'),
    path('saved-voices/', get_saved_voices, name='saved-voices'),
    path('saved-voice/<uuid:voice_id>/', get_saved_voice_details, name='saved-voice-details'),
]
