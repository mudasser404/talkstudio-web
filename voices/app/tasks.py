# voices/tasks.py
import os
import uuid
import logging
from datetime import datetime
from celery import shared_task
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.contrib.auth import get_user_model
from voices.progress_tracker import VoiceGenerationTracker
from accounts.models import CreditTransaction, Notification

# Yeh tumhara F5-TTS wrapper path change kar lena
from tts_engine.f5tts_wrapper import get_f5tts_wrapper  # ← apna correct path daal do

logger = logging.getLogger(__name__)

@shared_task(bind=True)
def smart_f5tts_generation_task(
    self, task_id, text, ref_audio_path, ref_text, speed,
    nfe_step, credits, user_id=None, language='multilingual', cfg_strength=2.0
):
    """Actual generation — yeh GPU worker mein chalega"""
    logger.info(f"GPU {os.environ.get('CUDA_VISIBLE_DEVICES', 'CPU')} pe generation start — Task {task_id}")

    try:
        VoiceGenerationTracker.start_processing(task_id)
        VoiceGenerationTracker.update_progress(task_id, 20)

        # Load model on THIS GPU
        model_wrapper = get_f5tts_wrapper()
        model_wrapper.load_model()  # har worker apna model load karega

        result = model_wrapper.generate(
            text=text,
            reference_audio=ref_audio_path,
            reference_text=ref_text or "",
            speed=speed,
            nfe_step=nfe_step,
            cfg_strength=cfg_strength,
            language=language
        )

        if not result['success']:
            raise Exception(result.get('error', 'Generation failed'))

        VoiceGenerationTracker.update_progress(task_id, 80)

        # Save final audio
        audio_file = f'voice_{uuid.uuid4().hex}.wav'
        audio_path = f'voices/{datetime.now().strftime("%Y/%m/%d")}/{audio_file}'
        with open(result['audio_path'], 'rb') as f:
            saved_path = default_storage.save(audio_path, ContentFile(f.read()))

        duration = result.get('duration', 0)
        VoiceGenerationTracker.mark_completed(task_id, saved_path, os.path.getsize(result['audio_path']), duration)

        # Deduct credits
        if user_id:
            User = get_user_model()
            user = User.objects.get(id=user_id)
            user.deduct_credits(credits)
            CreditTransaction.objects.create(
                user=user, amount=-credits,
                transaction_type='usage',
                description=f'TalkStudio TTS: {len(text)} chars'
            )

        # Cleanup temp files
        for path in [result['audio_path'], ref_audio_path]:
            if os.path.exists(path):
                os.remove(path)

        logger.info(f"Generation SUCCESS → {saved_path}")

    except Exception as e:
        logger.error(f"Generation FAILED: {e}", exc_info=True)
        VoiceGenerationTracker.mark_failed(task_id, str(e))