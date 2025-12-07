from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class TtsEngineConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tts_engine'

    # DISABLED ready() - was causing 502 errors
    # Model will load on first request (original behavior)
