"""TalkStudio TTS Integration for Django TTS Engine - API Based"""
import os, logging, uuid
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from django.shortcuts import render
from django.http import JsonResponse, FileResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.contrib.auth.decorators import login_required

logger = logging.getLogger(__name__)

# Thread pool for background generation
_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="voice_gen")

# TTS API Service instance
_tts_service = None

def get_tts_service():
    """Get TTS API Service singleton"""
    global _tts_service
    if _tts_service is None:
        from .tts_api_service import get_tts_api_service
        _tts_service = get_tts_api_service()
    return _tts_service


def index_tts_studio(request):
    """Render TTS Studio page"""
    tts = get_tts_service()
    return render(request, "clone.html", {
        "page_title": "TalkStudio",
        "model_available": tts.is_available,
        "max_characters": settings.MAX_TEXT_LENGTH,
        "credits_per_character": settings.CREDITS_PER_CHARACTER,
    })


def _generate_in_background(task_id, text, ref_audio, ref_text, speed, nfe_step, credits, user_id, language='multilingual', cfg_strength=2.0):
    """Background task for voice generation using API"""
    from voices.progress_tracker import VoiceGenerationTracker
    from accounts.models import CreditTransaction, Notification
    from django.contrib.auth import get_user_model

    # Get TTS API service
    tts_service = get_tts_service()

    logger.info(f"Background task STARTED for task_id: {task_id}")
    logger.info(f"Text length: {len(text)} chars")
    logger.info(f"Reference audio: {ref_audio}")
    logger.info(f"Speed: {speed}, NFE Steps: {nfe_step}, CFG Strength: {cfg_strength}")
    logger.info(f"Language: {language}")

    try:
        logger.info(f"Starting processing for task: {task_id}")
        VoiceGenerationTracker.start_processing(task_id)
        VoiceGenerationTracker.update_progress(task_id, 20)
        logger.info(f"Progress updated to 20% for task: {task_id}")

        # Generate voice using TTS API
        logger.info(f"Calling TTS API for generation...")

        result = tts_service.generate(
            text=text,
            reference_audio=ref_audio,
            reference_text=ref_text,
            speed=speed,
            remove_silence=False,
            nfe_step=nfe_step,
            clean_audio=True,
            noise_reduction_strength=0.3,
            cfg_strength=cfg_strength,
            sway_sampling_coef=-1.0,
            language=language
        )

        logger.info(f"TTS API generation completed. Success: {result.get('success')}")

        VoiceGenerationTracker.update_progress(task_id, 80)

        if result['success']:
            audio_file = f'voice_{uuid.uuid4().hex}.wav'
            audio_path = f'voices/{datetime.now().strftime("%Y/%m/%d")}/{audio_file}'

            with open(result['audio_path'], 'rb') as f:
                saved_path = default_storage.save(audio_path, ContentFile(f.read()))

            VoiceGenerationTracker.mark_completed(task_id, saved_path,
                                                 result['file_size'], result['duration'])

            if user_id:
                user = get_user_model().objects.get(id=user_id)
                user.deduct_credits(credits)
                CreditTransaction.objects.create(user=user, amount=-credits,
                    transaction_type='usage', description=f'TalkStudio: {len(text)} chars',
                    balance_after=user.credits)

                # Send notifications
                # 1. Voice generation success notification
                Notification.create_notification(
                    user=user,
                    title='Voice Generation Complete',
                    message=f'Your voice has been generated successfully! Generated {len(text)} characters using TalkStudio.',
                    notification_type='success',
                    link='/dashboard',
                    metadata={
                        'task_id': str(task_id),
                        'character_count': len(text),
                        'duration': result.get('duration', 0),
                        'model': 'TalkStudio'
                    }
                )

                # 2. Credit deduction notification
                Notification.create_notification(
                    user=user,
                    title='Credits Deducted',
                    message=f'{credits} credits have been deducted from your account. Remaining balance: {user.credits} credits.',
                    notification_type='info',
                    link='/dashboard',
                    metadata={
                        'credits_used': credits,
                        'balance_after': user.credits,
                        'reason': 'Voice generation'
                    }
                )

                # 3. Low credits warning if balance is low
                if user.credits < 100:  # Warning threshold
                    Notification.notify_credits_low(user, user.credits)

            # Cleanup temp files
            try:
                os.remove(result['audio_path'])
                if os.path.exists(ref_audio):
                    os.remove(ref_audio)
                    logger.info(f"Cleaned up reference audio: {ref_audio}")
            except Exception as cleanup_error:
                logger.warning(f"Cleanup error: {cleanup_error}")

        else:
            error_msg = result.get('error', 'Unknown error')
            logger.error(f"Generation failed for task {task_id}: {error_msg}")
            VoiceGenerationTracker.mark_failed(task_id, error_msg)

            # Cleanup reference audio even on failure
            try:
                if os.path.exists(ref_audio):
                    os.remove(ref_audio)
            except Exception:
                pass

            # Send failure notification to user
            if user_id:
                user = get_user_model().objects.get(id=user_id)
                Notification.create_notification(
                    user=user,
                    title='Voice Generation Failed',
                    message=f'Failed to generate voice: {error_msg}',
                    notification_type='error',
                    link='/clone',
                    metadata={
                        'task_id': str(task_id),
                        'error': error_msg
                    }
                )

    except Exception as e:
        logger.error(f"EXCEPTION in background task {task_id}: {str(e)}", exc_info=True)
        VoiceGenerationTracker.mark_failed(task_id, str(e))

        # Send exception notification to user
        if user_id:
            try:
                user = get_user_model().objects.get(id=user_id)
                Notification.create_notification(
                    user=user,
                    title='Voice Generation Error',
                    message=f'An error occurred during voice generation: {str(e)}',
                    notification_type='error',
                    link='/clone',
                    metadata={
                        'task_id': str(task_id),
                        'error': str(e)
                    }
                )
            except Exception as notify_error:
                logger.error(f"Failed to send error notification: {notify_error}")


@csrf_exempt
@require_http_methods(["POST"])
def generate_speech(request):
    """Generate speech endpoint - uses external API"""
    try:
        from voices.progress_tracker import VoiceGenerationTracker

        tts_service = get_tts_service()
        if not tts_service.is_available:
            return JsonResponse({
                'success': False,
                'error': 'TTS API service not configured. Please contact administrator.'
            }, status=503)

        user = request.user if request.user.is_authenticated else None
        text = request.POST.get('text', '').strip()
        ref_text = request.POST.get('reference_text', '').strip()
        speed = float(request.POST.get('speed', 1.0))
        pitch = float(request.POST.get('pitch', 1.0))
        usage_type = request.POST.get('usage_type', 'short')
        language = request.POST.get('language', 'multilingual')

        # Get emotion control settings
        emotion_method = int(request.POST.get('emotion_method', 0))
        emotion_weight = float(request.POST.get('emotion_weight', 1.0))
        emotion_text = request.POST.get('emotion_text', '').strip()

        if not text:
            return JsonResponse({'success': False, 'error': 'Text required'}, status=400)

        if len(text) > settings.MAX_TEXT_LENGTH:
            return JsonResponse({'success': False, 'error': 'Text too long'}, status=400)

        credits = len(text) * settings.CREDITS_PER_CHARACTER
        if user and user.credits < credits:
            return JsonResponse({'success': False, 'error': 'Insufficient credits'}, status=400)

        if 'reference_audio' not in request.FILES:
            return JsonResponse({'success': False, 'error': 'Reference audio required'}, status=400)

        ref_audio = request.FILES['reference_audio']
        # Generate unique filename with timestamp to avoid conflicts
        unique_id = uuid.uuid4().hex
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = ''.join(c for c in ref_audio.name if c.isalnum() or c in '._-')[:50]
        ref_file = f'ref_{timestamp}_{unique_id}_{safe_filename}'
        ref_path = f'references/{datetime.now().strftime("%Y/%m/%d")}/{ref_file}'

        # Save with unique path to avoid race conditions
        ref_saved = default_storage.save(ref_path, ContentFile(ref_audio.read()))
        logger.info(f"Reference audio saved: {ref_saved}")

        # Calculate nfe_step based on usage type
        nfe_step = 64 if usage_type == 'long' else 32

        # Process emotion control
        cfg_strength = 2.0  # Default
        adjusted_speed = speed

        # Parse emotion vectors if method is 2 (Manual Control)
        if emotion_method == 2:
            try:
                import json
                emotion_vectors_str = request.POST.get('emotion_vectors', '[]')
                emotion_vectors = json.loads(emotion_vectors_str)

                # Emotion vectors: [Happy, Sad, Angry, Surprise, Fear, Disgust, Contempt, Neutral]
                if len(emotion_vectors) >= 8:
                    happy = emotion_vectors[0]
                    sad = emotion_vectors[1]
                    angry = emotion_vectors[2]

                    # Adjust cfg_strength based on dominant emotion
                    if happy > 0.5:
                        cfg_strength = 2.5 + (happy * emotion_weight)
                        adjusted_speed = speed * (1.0 + happy * 0.2)
                    elif sad > 0.5:
                        cfg_strength = 1.5 - (sad * 0.5 * emotion_weight)
                        adjusted_speed = speed * (1.0 - sad * 0.15)
                    elif angry > 0.5:
                        cfg_strength = 3.0 + (angry * emotion_weight)
                        adjusted_speed = speed * (1.0 + angry * 0.1)
            except:
                pass  # Use defaults if parsing fails

        task = VoiceGenerationTracker.create_task(user=user, text=text,
            voice_source='custom', speed=speed,
            generation_params={'model': 'TalkStudio', 'ref_text': ref_text, 'usage_type': usage_type, 'nfe_step': nfe_step, 'language': language})

        # Submit to background thread pool
        logger.info(f"Submitting task {task.id} to worker pool")
        _executor.submit(
            _generate_in_background,
            task.id, text, default_storage.path(ref_saved), ref_text, adjusted_speed,
            nfe_step, credits, user.id if user else None, language, cfg_strength
        )

        logger.info(f"Task {task.id} queued successfully.")

        return JsonResponse({
            'success': True, 'task_id': str(task.id), 'status': 'pending',
            'estimated_time': task.estimated_time, 'character_count': len(text),
            'credits_needed': credits, 'model': 'TalkStudio'
        })
    except Exception as e:
        logger.error(f"Generation error: {str(e)}", exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def analyze_emotion(request):
    """Emotion analysis endpoint - not supported"""
    return JsonResponse({'success': False, 'error': 'Not supported'})


@require_http_methods(["GET"])
def get_model_info(request):
    """Get model/service info"""
    tts_service = get_tts_service()
    return JsonResponse({
        'success': tts_service.is_available,
        'available': tts_service.is_available,
        'model_name': 'TalkStudio',
        'features': {'voice_cloning': True, 'speed_control': True}
    })


@require_http_methods(["GET"])
def download_audio(request, filename):
    """Download generated audio file"""
    try:
        fp = Path(settings.MEDIA_ROOT) / 'generated' / filename
        if not fp.exists():
            return JsonResponse({'success': False}, status=404)
        return FileResponse(open(fp, 'rb'), as_attachment=True)
    except:
        return JsonResponse({'success': False}, status=500)


@login_required
@require_http_methods(["GET"])
def get_generation_history(request):
    """Get generation history for user"""
    return JsonResponse({'success': True, 'history': []})


@csrf_exempt
def check_progress(request, task_id):
    """Check task progress"""
    from voices.progress_tracker import ProgressTracker
    p = ProgressTracker.get_progress(task_id)
    return JsonResponse({'success': bool(p), **p} if p else {'success': False})


@csrf_exempt
@require_http_methods(["GET"])
def get_generation_progress(request, task_id):
    """Get detailed generation progress"""
    from voices.progress_tracker import VoiceGenerationTracker
    return JsonResponse(VoiceGenerationTracker.get_status(task_id))
