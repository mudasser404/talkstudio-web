from django.db import models
from django.conf import settings
import uuid
from voice_cloning.compression_utils import compress_image


class VoiceLibrary(models.Model):
    """Default voice library with male/female voices"""
    name = models.CharField(max_length=100)
    gender = models.CharField(
        max_length=10,
        choices=[
            ('male', 'Male'),
            ('female', 'Female'),
            ('neutral', 'Neutral'),
        ]
    )
    accent = models.CharField(max_length=50)
    language = models.CharField(max_length=50, default='English')
    voice_file = models.FileField(upload_to='library_voices/')
    image = models.ImageField(upload_to='library_images/', null=True, blank=True)
    embedding_file = models.FileField(upload_to='library_embeddings/', null=True, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    preview_audio = models.FileField(upload_to='library_previews/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Voice Libraries'

    def save(self, *args, **kwargs):
        # Compress voice library image if uploaded
        if self.image and hasattr(self.image, 'file'):
            self.image = compress_image(self.image, quality=85, max_width=800, max_height=800)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.gender} - {self.accent})"


class ClonedVoice(models.Model):
    """User's cloned voices"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='cloned_voices'
    )
    name = models.CharField(max_length=100)
    audio_file = models.FileField(upload_to='cloned_voices/')
    image = models.ImageField(upload_to='voice_images/', null=True, blank=True)
    embedding_file = models.FileField(upload_to='voice_embeddings/', null=True, blank=True)
    duration = models.FloatField(help_text='Duration in seconds')
    file_size = models.IntegerField(help_text='File size in bytes')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        # Compress cloned voice image if uploaded
        if self.image and hasattr(self.image, 'file'):
            self.image = compress_image(self.image, quality=85, max_width=800, max_height=800)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} - {self.user.email}"


class GeneratedAudio(models.Model):
    """Generated TTS audio files"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='generated_audios',
        null=True,
        blank=True
    )
    text = models.TextField()
    voice_source = models.CharField(
        max_length=20,
        choices=[
            ('library', 'Library Voice'),
            ('cloned', 'Cloned Voice'),
            ('custom', 'Custom Voice Reference'),
        ],
        default='custom'
    )
    library_voice = models.ForeignKey(
        VoiceLibrary,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    cloned_voice = models.ForeignKey(
        ClonedVoice,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    audio_file = models.FileField(upload_to='generated_audio/%Y/%m/%d/', null=True, blank=True)

    # Voice parameters
    speed = models.FloatField(default=1.0)
    pitch = models.FloatField(default=1.0)
    tone = models.FloatField(default=1.0)

    # Generation parameters (stored as JSON for flexibility)
    generation_params = models.JSONField(
        default=dict,
        blank=True,
        help_text='Parameters used for audio generation (temperature, top_p, etc.)'
    )

    # Status tracking for real-time progress
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('processing', 'Processing'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
        ],
        default='pending'
    )
    progress = models.IntegerField(default=0, help_text='Progress percentage 0-100')
    estimated_time = models.IntegerField(null=True, blank=True, help_text='Estimated time in seconds')
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    # Metadata
    duration = models.FloatField(null=True, blank=True, help_text='Duration in seconds')
    file_size = models.IntegerField(default=0, help_text='File size in bytes')
    characters_used = models.IntegerField()
    credits_used = models.IntegerField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Generated Audios'
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.text[:50]}..."

    def get_file_size_display(self):
        """Return human-readable file size"""
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"

    def get_duration_display(self):
        """Return human-readable duration"""
        if not self.duration:
            return "Unknown"
        minutes = int(self.duration // 60)
        seconds = int(self.duration % 60)
        if minutes > 0:
            return f"{minutes}m {seconds}s"
        return f"{seconds}s"


class VoiceGenerationHistory(models.Model):
    """Track all voice generation attempts"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='generation_history'
    )
    generated_audio = models.ForeignKey(
        GeneratedAudio,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('processing', 'Processing'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
        ],
        default='pending'
    )
    error_message = models.TextField(blank=True)
    processing_time = models.FloatField(null=True, blank=True, help_text='Time in seconds')
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Voice Generation Histories'

    def __str__(self):
        return f"{self.user.email} - {self.status}"
