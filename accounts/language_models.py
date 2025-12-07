from django.db import models
from django.utils.translation import gettext_lazy as _


class SupportedLanguage(models.Model):
    """
    Model to manage which languages are enabled/disabled for TTS
    """
    language_code = models.CharField(
        max_length=10,
        unique=True,
        verbose_name=_("Language Code"),
        help_text=_("ISO language code (e.g., 'en', 'zh', 'es')")
    )
    language_name = models.CharField(
        max_length=100,
        verbose_name=_("Language Name"),
        help_text=_("Full language name (e.g., 'English', 'Chinese')")
    )
    native_name = models.CharField(
        max_length=100,
        verbose_name=_("Native Name"),
        help_text=_("Language name in native script (e.g., '中文', 'Español')")
    )
    flag_emoji = models.CharField(
        max_length=10,
        default="🌐",
        verbose_name=_("Flag Emoji"),
        help_text=_("Flag emoji for the language")
    )
    is_enabled = models.BooleanField(
        default=True,
        verbose_name=_("Enabled"),
        help_text=_("Whether this language is available for users")
    )
    is_trained = models.BooleanField(
        default=False,
        verbose_name=_("Model Trained"),
        help_text=_("Whether a model is trained for this language")
    )
    model_path = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name=_("Model Path"),
        help_text=_("Path to the trained model file")
    )
    training_status = models.CharField(
        max_length=20,
        choices=[
            ('not_started', _('Not Started')),
            ('training', _('Training')),
            ('completed', _('Completed')),
            ('failed', _('Failed')),
        ],
        default='not_started',
        verbose_name=_("Training Status")
    )
    quality_score = models.FloatField(
        default=0.0,
        verbose_name=_("Quality Score"),
        help_text=_("Model quality score (0-100)")
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("Description"),
        help_text=_("Additional information about this language model")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Supported Language")
        verbose_name_plural = _("Supported Languages")
        ordering = ['language_name']

    def __str__(self):
        status = "✓" if self.is_enabled else "✗"
        return f"{status} {self.flag_emoji} {self.language_name} ({self.language_code})"

    @property
    def display_name(self):
        """Returns formatted display name with flag"""
        return f"{self.flag_emoji} {self.language_name} ({self.native_name})"
