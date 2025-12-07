# voices/admin.py
from django.contrib import admin
from .models import VoiceLibrary, ClonedVoice, GeneratedAudio, VoiceGenerationHistory

@admin.register(VoiceLibrary)
class VoiceLibraryAdmin(admin.ModelAdmin):
    list_display = ['name', 'gender', 'accent', 'language', 'is_active', 'created_at']
    list_filter = ['gender', 'language', 'is_active', 'created_at']
    search_fields = ['name', 'accent', 'description']
    list_editable = ['is_active']

@admin.register(ClonedVoice)
class ClonedVoiceAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'duration', 'file_size', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'user__email']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(GeneratedAudio)
class GeneratedAudioAdmin(admin.ModelAdmin):
    list_display = ['user', 'voice_source', 'status', 'characters_used', 'credits_used', 'created_at']
    list_filter = ['voice_source', 'status', 'created_at']
    search_fields = ['text', 'user__email']
    readonly_fields = ['created_at']

@admin.register(VoiceGenerationHistory)
class VoiceGenerationHistoryAdmin(admin.ModelAdmin):
    list_display = ['user', 'status', 'processing_time', 'created_at', 'completed_at']
    list_filter = ['status', 'created_at']
    search_fields = ['user__email', 'error_message']
    readonly_fields = ['created_at', 'completed_at']