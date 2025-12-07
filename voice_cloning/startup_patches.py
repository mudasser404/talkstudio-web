"""Startup patches for Talk Studio"""
import logging
logger = logging.getLogger(__name__)

def initialize_tts_api():
    """Initialize TTS API Service at startup"""
    try:
        from tts_engine.tts_api_service import get_tts_api_service
        service = get_tts_api_service()
        if service.is_available:
            logger.info("TTS API Service initialized successfully")
        else:
            logger.warning("TTS API Service not configured - Set TTS_API_URL in settings")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize TTS API Service: {e}")
        return False

def apply_all_patches():
    logger.info("Applying startup patches...")
    initialize_tts_api()
    logger.info("Startup patches complete")
    return True

if __name__ != "__main__":
    apply_all_patches()
