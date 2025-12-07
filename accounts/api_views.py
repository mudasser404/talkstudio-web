"""
API views for key management and API access
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from .models import APIKey, User
import json


@login_required
@require_http_methods(["POST"])
def generate_api_key(request):
    """Generate a new API key for the user"""
    try:
        # Check if user has API access (Pro/Yearly plans or Admin)
        if not (request.user.can_use_api() or request.user.is_staff):
            return JsonResponse({
                'success': False,
                'error': 'API access is only available for Pro and Yearly plans. Please upgrade your plan.'
            }, status=403)

        data = json.loads(request.body)
        name = data.get('name', '').strip()

        if not name:
            return JsonResponse({
                'success': False,
                'error': 'Please provide a name for the API key'
            }, status=400)

        # Check if user already has 5 or more keys
        if request.user.api_keys.filter(is_active=True).count() >= 5:
            return JsonResponse({
                'success': False,
                'error': 'You can have a maximum of 5 active API keys. Please delete an existing key first.'
            }, status=400)

        # Create new API key
        api_key = APIKey.objects.create(
            user=request.user,
            name=name
        )

        return JsonResponse({
            'success': True,
            'api_key': {
                'id': api_key.id,
                'name': api_key.name,
                'key': api_key.key,
                'created_at': api_key.created_at.isoformat()
            },
            'message': 'API key generated successfully. Make sure to copy it now - you won\'t be able to see it again!'
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["GET"])
def list_api_keys(request):
    """List all API keys for the user"""
    try:
        keys = request.user.api_keys.filter(is_active=True).order_by('-created_at')

        return JsonResponse({
            'success': True,
            'keys': [
                {
                    'id': key.id,
                    'name': key.name,
                    'key_preview': f"{key.key[:20]}...",
                    'created_at': key.created_at.isoformat(),
                    'last_used': key.last_used.isoformat() if key.last_used else None
                }
                for key in keys
            ]
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["DELETE"])
def delete_api_key(request, key_id):
    """Delete an API key"""
    try:
        api_key = APIKey.objects.get(id=key_id, user=request.user)
        api_key.is_active = False
        api_key.save()

        return JsonResponse({
            'success': True,
            'message': 'API key deleted successfully'
        })

    except APIKey.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'API key not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# ============================================
# API Endpoints for External Use (with API Key Auth)
# ============================================

def get_user_from_api_key(request):
    """Helper function to authenticate user via API key"""
    auth_header = request.headers.get('Authorization', '')

    if not auth_header.startswith('Bearer '):
        return None, 'Missing or invalid Authorization header'

    api_key = auth_header.replace('Bearer ', '').strip()

    try:
        key_obj = APIKey.objects.get(key=api_key, is_active=True)

        # Update last used timestamp
        key_obj.last_used = timezone.now()
        key_obj.save(update_fields=['last_used'])

        return key_obj.user, None

    except APIKey.DoesNotExist:
        return None, 'Invalid API key'


@csrf_exempt
@require_http_methods(["POST"])
def api_generate_voice(request):
    """API endpoint to generate voice from text using F5-TTS"""
    # Authenticate user
    user, error = get_user_from_api_key(request)
    if error:
        return JsonResponse({
            'success': False,
            'error': error
        }, status=401)

    try:
        data = json.loads(request.body)
        text = data.get('text', '').strip()
        voice_id = data.get('voice_id')
        language = data.get('language', 'multilingual')
        speed = float(data.get('speed', 1.0))
        nfe_step = int(data.get('nfe_step', 32))  # Quality: 16=fast, 32=high quality

        if not text:
            return JsonResponse({
                'success': False,
                'error': 'Text is required'
            }, status=400)

        if not voice_id:
            return JsonResponse({
                'success': False,
                'error': 'Voice ID is required'
            }, status=400)

        # Calculate credits needed
        from django.conf import settings
        credits_needed = len(text) * getattr(settings, 'CREDITS_PER_CHARACTER', 1)

        # Check if user has enough credits
        if user.credits < credits_needed:
            return JsonResponse({
                'success': False,
                'error': f'Insufficient credits. Need {credits_needed} credits, you have {user.credits}.'
            }, status=403)

        # Get the saved voice
        from voices.models import ClonedVoice
        try:
            voice = ClonedVoice.objects.get(id=voice_id, user=user)
        except ClonedVoice.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': f'Voice not found or you do not have access to voice ID: {voice_id}'
            }, status=404)

        # Import TTS engine
        from tts_engine.f5tts_wrapper import get_f5tts_wrapper
        tts_model = get_f5tts_wrapper()

        if not tts_model.model_loaded:
            tts_model.load_model()

        if not tts_model.model_loaded:
            return JsonResponse({
                'success': False,
                'error': 'TTS model failed to load. Please try again later.'
            }, status=500)

        # Generate audio using F5-TTS
        import uuid
        from datetime import datetime
        from django.core.files.storage import default_storage
        from django.core.files.base import ContentFile
        import os

        result = tts_model.generate(
            text=text,
            reference_audio=voice.audio_file.path,
            reference_text=getattr(voice, 'reference_text', ''),
            speed=speed,
            nfe_step=nfe_step,
            remove_silence=True,
            clean_audio=True,
            noise_reduction_strength=0.5,
            language=language
        )

        if not result['success']:
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Voice generation failed')
            }, status=500)

        # Save generated audio to media storage
        audio_file = f'api_voice_{uuid.uuid4().hex}.wav'
        audio_path = f'api_generated/{datetime.now().strftime("%Y/%m/%d")}/{audio_file}'

        with open(result['audio_path'], 'rb') as f:
            saved_path = default_storage.save(audio_path, ContentFile(f.read()))

        # Build full URL
        audio_url = request.build_absolute_uri(default_storage.url(saved_path))

        # Deduct credits
        user.deduct_credits(credits_needed)

        # Create credit transaction
        from accounts.models import CreditTransaction
        CreditTransaction.objects.create(
            user=user,
            amount=-credits_needed,
            transaction_type='usage',
            description=f'API TTS: {len(text)} chars via API',
            balance_after=user.credits
        )

        # Cleanup temporary file
        try:
            os.remove(result['audio_path'])
        except:
            pass

        return JsonResponse({
            'success': True,
            'audio_url': audio_url,
            'duration': result.get('duration', 0),
            'file_size': result.get('file_size', 0),
            'credits_used': credits_needed,
            'credits_remaining': user.credits,
            'character_count': len(text),
            'language': language,
            'model': 'F5-TTS'
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"API voice generation error: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def api_list_voices(request):
    """API endpoint to list user's saved voices"""
    # Authenticate user
    user, error = get_user_from_api_key(request)
    if error:
        return JsonResponse({
            'success': False,
            'error': error
        }, status=401)

    try:
        # Get user's saved voices
        from voices.models import ClonedVoice
        import os
        voices = ClonedVoice.objects.filter(user=user).order_by('-created_at')

        voice_list = []
        for voice in voices:
            # Safely get file info - check if file actually exists
            audio_url = None
            file_size = 0
            file_exists = False

            if voice.audio_file:
                try:
                    # Check if file exists on disk
                    if hasattr(voice.audio_file, 'path') and os.path.exists(voice.audio_file.path):
                        audio_url = request.build_absolute_uri(voice.audio_file.url)
                        file_size = voice.audio_file.size
                        file_exists = True
                    else:
                        # File reference exists but file is missing
                        audio_url = None
                        file_size = 0
                        file_exists = False
                except Exception:
                    # Handle any file access errors
                    audio_url = None
                    file_size = 0
                    file_exists = False

            voice_list.append({
                'id': str(voice.id),
                'name': voice.name,
                'audio_url': audio_url,
                'created_at': voice.created_at.isoformat(),
                'file_size': file_size,
                'file_exists': file_exists
            })

        return JsonResponse({
            'success': True,
            'count': len(voice_list),
            'voices': voice_list
        })

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"API list voices error: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_clone_voice(request):
    """API endpoint to save a new voice for cloning"""
    # Authenticate user
    user, error = get_user_from_api_key(request)
    if error:
        return JsonResponse({
            'success': False,
            'error': error
        }, status=401)

    try:
        # Check if user can create more voice clones
        max_clones = user.get_max_voice_clones()
        from voices.models import ClonedVoice
        current_clones = ClonedVoice.objects.filter(user=user).count()

        if max_clones != -1 and current_clones >= max_clones:
            return JsonResponse({
                'success': False,
                'error': f'You have reached the maximum number of voice clones ({max_clones}) for your plan. Please upgrade to create more.'
            }, status=403)

        # Get form data
        audio_file = request.FILES.get('audio_file')
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '')
        reference_text = request.POST.get('reference_text', '')

        if not audio_file:
            return JsonResponse({
                'success': False,
                'error': 'Audio file is required (multipart/form-data)'
            }, status=400)

        if not name:
            return JsonResponse({
                'success': False,
                'error': 'Voice name is required'
            }, status=400)

        # Validate file type
        allowed_types = ['.wav', '.mp3', '.ogg', '.flac', '.m4a']
        file_ext = audio_file.name.lower().split('.')[-1]
        if f'.{file_ext}' not in allowed_types:
            return JsonResponse({
                'success': False,
                'error': f'Invalid file type. Allowed: {", ".join(allowed_types)}'
            }, status=400)

        # Validate file size (max 50MB)
        max_size = 50 * 1024 * 1024  # 50MB
        if audio_file.size > max_size:
            return JsonResponse({
                'success': False,
                'error': f'File too large. Maximum size: 50MB'
            }, status=400)

        # Get audio duration using mutagen or fallback
        duration = 0.0
        try:
            import tempfile
            import os

            # Save to temp file to read duration
            with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_ext}') as tmp:
                for chunk in audio_file.chunks():
                    tmp.write(chunk)
                tmp_path = tmp.name

            # Try to get duration using mutagen
            try:
                from mutagen import File as MutagenFile
                audio_info = MutagenFile(tmp_path)
                if audio_info and audio_info.info:
                    duration = audio_info.info.length
            except ImportError:
                # Fallback: try pydub
                try:
                    from pydub import AudioSegment
                    audio_segment = AudioSegment.from_file(tmp_path)
                    duration = len(audio_segment) / 1000.0  # milliseconds to seconds
                except:
                    # Fallback: estimate from file size (rough estimate)
                    # Assume ~128kbps for compressed, ~1.5MB/min for wav
                    if file_ext == 'wav':
                        duration = audio_file.size / (44100 * 2 * 2)  # 44.1kHz, 16-bit, stereo
                    else:
                        duration = audio_file.size / (128 * 1024 / 8)  # 128kbps

            # Clean up temp file
            os.unlink(tmp_path)

            # Reset file pointer for saving
            audio_file.seek(0)

        except Exception as e:
            # If all fails, use a default duration estimate
            duration = max(1.0, audio_file.size / (128 * 1024 / 8))  # Estimate based on 128kbps
            audio_file.seek(0)

        # Save the voice with required fields
        saved_voice = ClonedVoice.objects.create(
            user=user,
            name=name,
            audio_file=audio_file,
            duration=round(duration, 2),
            file_size=audio_file.size
        )

        # If free user, increment their voice clone count
        if user.subscription_type == 'free':
            user.free_voice_clones_used += 1
            user.save()

        return JsonResponse({
            'success': True,
            'voice_id': str(saved_voice.id),
            'name': saved_voice.name,
            'audio_url': request.build_absolute_uri(saved_voice.audio_file.url),
            'created_at': saved_voice.created_at.isoformat(),
            'file_size': saved_voice.file_size,
            'duration': saved_voice.duration,
            'message': 'Voice saved successfully. You can now use this voice_id to generate speech.'
        })

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"API clone voice error: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
