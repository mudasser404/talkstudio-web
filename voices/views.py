from rest_framework import viewsets, status, generics
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser
from django.conf import settings
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.views.decorators.http import require_http_methods
import os
import uuid
from .models import VoiceLibrary, ClonedVoice, GeneratedAudio, VoiceGenerationHistory
from .serializers import (
    VoiceLibrarySerializer,
    ClonedVoiceSerializer,
    ClonedVoiceCreateSerializer,
    GeneratedAudioSerializer,
    GeneratedAudioCreateSerializer,
    VoiceGenerationHistorySerializer
)
from accounts.models import CreditTransaction, PlatformSettings

User = get_user_model()


class VoiceLibraryViewSet(viewsets.ReadOnlyModelViewSet):
    """View default voice library"""
    serializer_class = VoiceLibrarySerializer
    permission_classes = [AllowAny]
    queryset = VoiceLibrary.objects.filter(is_active=True)

    @action(detail=False, methods=['get'])
    def by_gender(self, request):
        """Filter voices by gender"""
        gender = request.query_params.get('gender', None)
        if gender:
            voices = self.queryset.filter(gender=gender)
        else:
            voices = self.queryset
        serializer = self.get_serializer(voices, many=True)
        return Response(serializer.data)


class ClonedVoiceViewSet(viewsets.ModelViewSet):
    """Manage cloned voices"""
    serializer_class = ClonedVoiceSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        return ClonedVoice.objects.filter(user=self.request.user, is_active=True)

    def get_serializer_class(self):
        if self.action == 'create':
            return ClonedVoiceCreateSerializer
        return ClonedVoiceSerializer

    def create(self, request, *args, **kwargs):
        """Clone a new voice"""
        user = request.user

        # Check if user can clone voice (skip check for admin/superadmin)
        if not (user.is_staff or user.is_superuser):
            if not user.can_clone_voice():
                return Response({
                    'error': 'You have reached the maximum number of voice clones for your plan. Please upgrade.'
                }, status=status.HTTP_403_FORBIDDEN)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Save audio file
        audio_file = serializer.validated_data['audio_file']
        name = serializer.validated_data['name']
        image_file = serializer.validated_data.get('image', None)

        # Create unique filename for audio
        file_ext = os.path.splitext(audio_file.name)[1]
        filename = f"{uuid.uuid4()}{file_ext}"
        file_path = os.path.join(settings.MEDIA_ROOT, 'cloned_voices', filename)

        # Ensure directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # Save audio file
        with open(file_path, 'wb+') as destination:
            for chunk in audio_file.chunks():
                destination.write(chunk)

        # Handle image upload if provided
        image_filename = None
        if image_file:
            image_ext = os.path.splitext(image_file.name)[1]
            image_filename = f"{uuid.uuid4()}{image_ext}"
            image_path = os.path.join(settings.MEDIA_ROOT, 'voice_images', image_filename)
            os.makedirs(os.path.dirname(image_path), exist_ok=True)

            with open(image_path, 'wb+') as destination:
                for chunk in image_file.chunks():
                    destination.write(chunk)

        # Get audio duration and file size
        try:
            import wave
            import contextlib

            duration = 0
            try:
                with contextlib.closing(wave.open(file_path, 'r')) as f:
                    frames = f.getnframes()
                    rate = f.getframerate()
                    duration = frames / float(rate)
            except:
                # If not WAV, estimate duration as 10 seconds
                duration = 10.0

            file_size = os.path.getsize(file_path)
        except Exception as e:
            duration = 10.0
            file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0

        # Create ClonedVoice record without embedding for now
        cloned_voice = ClonedVoice.objects.create(
            user=user,
            name=name,
            audio_file=f"cloned_voices/{filename}",
            image=f"voice_images/{image_filename}" if image_filename else None,
            embedding_file=None,  # Will be generated when used
            duration=duration,
            file_size=file_size
        )

        # Update free voice clone count if free user
        if user.subscription_type == 'free':
            user.free_voice_clones_used += 1
            user.save()

        return Response({
            'message': 'Voice cloned successfully',
            'voice': ClonedVoiceSerializer(cloned_voice, context={'request': request}).data
        }, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        """Delete a cloned voice"""
        instance = self.get_object()
        instance.is_active = False
        instance.save()
        return Response({'message': 'Voice deleted successfully'}, status=status.HTTP_200_OK)


class GeneratedAudioViewSet(viewsets.ModelViewSet):
    """Manage generated audio"""
    serializer_class = GeneratedAudioSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return GeneratedAudio.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.action == 'create':
            return GeneratedAudioCreateSerializer
        return GeneratedAudioSerializer

    def create(self, request, *args, **kwargs):
        """Generate speech from text"""
        user = request.user
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        text = serializer.validated_data['text']
        voice_source = serializer.validated_data['voice_source']
        speed = serializer.validated_data.get('speed', 1.0)
        pitch = serializer.validated_data.get('pitch', 1.0)
        tone = serializer.validated_data.get('tone', 1.0)

        # Get platform settings for dynamic credit calculation
        platform_settings = PlatformSettings.get_settings()

        # Calculate credits needed based on dynamic settings
        if platform_settings.credit_calculation_type == 'per_character':
            units_count = len(text)
            unit_name = 'characters'
        elif platform_settings.credit_calculation_type == 'per_word':
            units_count = len(text.split())
            unit_name = 'words'
        elif platform_settings.credit_calculation_type == 'per_letter':
            # Count only letters (excluding spaces, punctuation)
            units_count = sum(c.isalpha() for c in text)
            unit_name = 'letters'
        else:
            # Fallback to character-based
            units_count = len(text)
            unit_name = 'characters'

        credits_needed = units_count * platform_settings.credits_per_unit

        # Check if user has enough credits
        if user.credits < credits_needed:
            return Response({
                'error': f'Insufficient credits. You need {credits_needed} credits but have {user.credits}.'
            }, status=status.HTTP_403_FORBIDDEN)

        # Get voice
        library_voice = None
        cloned_voice = None
        voice_embedding_path = None

        if voice_source == 'library':
            library_voice_id = serializer.validated_data.get('library_voice_id')
            try:
                library_voice = VoiceLibrary.objects.get(id=library_voice_id, is_active=True)
                voice_embedding_path = library_voice.embedding_file.path
            except VoiceLibrary.DoesNotExist:
                return Response({
                    'error': 'Library voice not found'
                }, status=status.HTTP_404_NOT_FOUND)
        else:
            cloned_voice_id = serializer.validated_data.get('cloned_voice_id')
            try:
                cloned_voice = ClonedVoice.objects.get(
                    id=cloned_voice_id,
                    user=user,
                    is_active=True
                )
                voice_embedding_path = cloned_voice.embedding_file.path
            except ClonedVoice.DoesNotExist:
                return Response({
                    'error': 'Cloned voice not found'
                }, status=status.HTTP_404_NOT_FOUND)

        # Create generation history record
        history = VoiceGenerationHistory.objects.create(
            user=user,
            status='processing'
        )

        try:
            # Generate audio using IndexTTS2
            # TTS model not configured yet
            # # TTS model not configured
            output_filename = f"{uuid.uuid4()}.wav"
            output_path = os.path.join(settings.MEDIA_ROOT, 'generated_audio', output_filename)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # Use the original audio file as speaker reference (not embedding)
            if voice_source == 'library':
                speaker_audio_path = library_voice.voice_file.path
            else:
                speaker_audio_path = cloned_voice.audio_file.path

            # Convert emotion parameters to IndexTTS2 format
            emotion_vectors = None
            if tone != 1.0:
                # Map tone parameter to emotion vectors
                # Simple mapping: higher tone = happier
                happy_level = max(0, min(1, tone - 0.5) * 2)
                emotion_vectors = [happy_level, 0, 0, 0, 0, 0, 0, 0]

            generation_result = indextts.generate_speech(
                text=text,
                speaker_audio_path=speaker_audio_path,
                output_path=output_path,
                emotion_control_method=2 if emotion_vectors else 0,
                emotion_vectors=emotion_vectors,
                temperature=0.8 * (1.0 / max(speed, 0.1)),  # Adjust temp based on speed
                top_p=0.8,
                top_k=30,
                num_beams=3
            )

            if not generation_result['success']:
                history.status = 'failed'
                history.error_message = generation_result.get('error', 'Unknown error')
                history.completed_at = timezone.now()
                history.save()

                return Response({
                    'error': f"Audio generation failed: {generation_result.get('error', 'Unknown error')}"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # Create GeneratedAudio record
            generated_audio = GeneratedAudio.objects.create(
                user=user,
                text=text,
                voice_source=voice_source,
                library_voice=library_voice,
                cloned_voice=cloned_voice,
                audio_file=f"generated_audio/{output_filename}",
                speed=speed,
                pitch=pitch,
                tone=tone,
                duration=generation_result['duration'],
                file_size=generation_result['file_size'],
                characters_used=units_count,  # Now stores units based on calculation type
                credits_used=credits_needed
            )

            # Deduct credits
            user.deduct_credits(credits_needed)

            # Create credit transaction with dynamic description
            CreditTransaction.objects.create(
                user=user,
                amount=-credits_needed,
                transaction_type='usage',
                description=f"Generated audio from text ({units_count} {unit_name}, {credits_needed} credits)",
                balance_after=user.credits
            )

            # Update history
            history.status = 'completed'
            history.generated_audio = generated_audio
            history.completed_at = timezone.now()
            history.save()

            return Response({
                'message': 'Audio generated successfully',
                'audio': GeneratedAudioSerializer(generated_audio).data,
                'credits_remaining': user.credits
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            history.status = 'failed'
            history.error_message = str(e)
            history.completed_at = timezone.now()
            history.save()

            return Response({
                'error': f"An error occurred: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class VoiceGenerationHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """View generation history"""
    serializer_class = VoiceGenerationHistorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return VoiceGenerationHistory.objects.filter(user=self.request.user)


from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.core.files import File


@api_view(['POST'])
@permission_classes([AllowAny])  # Allow access with X-User-ID header
def generate_audio_from_gradio(request):
    """
    API endpoint for Gradio to generate audio and track it.
    Expected data:
    - text: Input text for generation
    - audio_file_path: Path to generated audio file (on server)
    - generation_params: JSON object with generation parameters
    - voice_reference_name: Optional name of voice reference
    """
    # Try to get user from session first
    if request.user.is_authenticated:
        user = request.user
    else:
        # Try to get user from X-User-ID header (for Gradio integration)
        user_id = request.headers.get('X-User-ID')
        if not user_id:
            return Response({
                'error': 'Not authenticated'
            }, status=status.HTTP_401_UNAUTHORIZED)

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({
                'error': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)

    text = request.data.get('text')
    audio_file_path = request.data.get('audio_file_path')
    generation_params = request.data.get('generation_params', {})
    voice_reference_name = request.data.get('voice_reference_name', '')

    if not text or not audio_file_path:
        return Response({
            'error': 'Missing required fields: text and audio_file_path'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Get platform settings for dynamic credit calculation
    platform_settings = PlatformSettings.get_settings()

    # Calculate credits needed based on dynamic settings
    if platform_settings.credit_calculation_type == 'per_character':
        units_count = len(text)
        unit_name = 'characters'
    elif platform_settings.credit_calculation_type == 'per_word':
        units_count = len(text.split())
        unit_name = 'words'
    elif platform_settings.credit_calculation_type == 'per_letter':
        # Count only letters (excluding spaces, punctuation)
        units_count = sum(c.isalpha() for c in text)
        unit_name = 'letters'
    else:
        # Fallback to character-based
        units_count = len(text)
        unit_name = 'characters'

    credits_needed = units_count * platform_settings.credits_per_unit

    # Check if user has enough credits
    if user.credits < credits_needed:
        return Response({
            'error': f'Insufficient credits. You need {credits_needed} credits but have {user.credits}.',
            'credits_needed': credits_needed,
            'credits_available': user.credits
        }, status=status.HTTP_403_FORBIDDEN)

    try:
        # Check if file exists
        if not os.path.exists(audio_file_path):
            return Response({
                'error': 'Audio file not found on server'
            }, status=status.HTTP_404_NOT_FOUND)

        # Get file info
        file_size = os.path.getsize(audio_file_path)
        file_name = os.path.basename(audio_file_path)

        # Get audio duration (optional, requires pydub)
        duration = None
        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_file(audio_file_path)
            duration = len(audio) / 1000.0  # Convert to seconds
        except:
            pass

        # Create GeneratedAudio record by copying the file to media directory
        # Create a date-based subdirectory
        from datetime import datetime
        date_path = datetime.now().strftime('%Y/%m/%d')
        media_subdir = os.path.join('generated_audio', date_path)
        media_dir = os.path.join(settings.MEDIA_ROOT, media_subdir)
        os.makedirs(media_dir, exist_ok=True)

        # Create unique filename
        new_filename = f"{uuid.uuid4()}.wav"
        new_file_path = os.path.join(media_dir, new_filename)

        # Copy file to media directory
        import shutil
        shutil.copy2(audio_file_path, new_file_path)

        # Create database record
        generated_audio = GeneratedAudio.objects.create(
            user=user,
            text=text,
            voice_source='custom',
            audio_file=os.path.join(media_subdir, new_filename),
            speed=1.0,
            pitch=1.0,
            tone=1.0,
            generation_params=generation_params,
            duration=duration,
            file_size=file_size,
            characters_used=units_count,
            credits_used=credits_needed
        )

        # Deduct credits
        user.deduct_credits(credits_needed)

        # Create credit transaction
        CreditTransaction.objects.create(
            user=user,
            amount=-credits_needed,
            transaction_type='usage',
            description=f"Generated audio from Gradio ({units_count} {unit_name}, {credits_needed} credits)",
            balance_after=user.credits
        )

        # Create notification
        from accounts.models import Notification
        Notification.notify_audio_generated(user, units_count)

        return Response({
            'success': True,
            'message': 'Audio generated and tracked successfully',
            'audio_id': str(generated_audio.id),
            'credits_used': credits_needed,
            'credits_remaining': user.credits,
            'units_used': units_count,
            'unit_type': unit_name
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response({
            'error': f'An error occurred: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])  # Allow access with X-User-ID header
def get_user_credit_info(request):
    """Get user's current credit information and pricing settings"""
    # Try to get user from session first
    if request.user.is_authenticated:
        user = request.user
    else:
        # Try to get user from X-User-ID header (for Gradio integration)
        user_id = request.headers.get('X-User-ID')
        if not user_id:
            return Response({
                'error': 'Not authenticated'
            }, status=status.HTTP_401_UNAUTHORIZED)

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({
                'error': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)

    platform_settings = PlatformSettings.get_settings()

    return Response({
        'credits_available': user.credits,
        'credit_calculation_type': platform_settings.credit_calculation_type,
        'credits_per_unit': platform_settings.credits_per_unit,
        'free_trial_credits': platform_settings.free_trial_credits,
        'subscription_type': user.subscription_type
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_current_user_info(request):
    """
    Get currently logged-in user's information
    This endpoint requires Django session authentication
    """
    user = request.user
    platform_settings = PlatformSettings.get_settings()

    return Response({
        'success': True,
        'user': {
            'id': user.id,
            'email': user.email,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
        },
        'credits': {
            'available': user.credits,
            'calculation_type': platform_settings.credit_calculation_type,
            'credits_per_unit': platform_settings.credits_per_unit,
        },
        'subscription': {
            'type': user.subscription_type,
            'plan': user.subscription_plan.name if user.subscription_plan else None,
        }
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_gradio_access_token(request):
    """
    Generate a temporary token for Gradio access
    Returns the user ID that Gradio can use for authentication
    """
    user = request.user

    # For now, simply return the user ID
    # In production, you might want to generate a proper JWT token
    return Response({
        'success': True,
        'user_id': user.id,
        'email': user.email,
        'token': f"user_{user.id}"  # Simple token for now
    })


from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

@login_required
def open_gradio_ui(request):
    """
    Redirect to Gradio UI with user_id parameter
    """
    gradio_url = f"http://127.0.0.1:7860/?user_id={request.user.id}"
    return redirect(gradio_url)


from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import librosa


@require_http_methods(["POST"])
@login_required
def save_reference_voice(request):
    """
    Save uploaded reference voice for later use
    Simple endpoint for clone.html UI
    """
    try:
        user = request.user
        title = request.POST.get('title', '').strip()

        if not title:
            return JsonResponse({
                'success': False,
                'error': 'Voice title is required'
            }, status=400)

        if 'audio' not in request.FILES:
            return JsonResponse({
                'success': False,
                'error': 'Audio file is required'
            }, status=400)

        audio_file = request.FILES['audio']

        # Save audio file
        from django.core.files.storage import default_storage
        from django.core.files.base import ContentFile
        filename = f'ref_{uuid.uuid4().hex}_{audio_file.name}'
        file_path = f'cloned_voices/{timezone.now().strftime("%Y/%m/%d")}/{filename}'
        saved_path = default_storage.save(file_path, ContentFile(audio_file.read()))
        full_path = default_storage.path(saved_path)

        # Get audio duration using librosa
        try:
            y, sr = librosa.load(full_path, sr=None)
            duration = len(y) / sr
        except:
            duration = 0

        # Get file size
        file_size = default_storage.size(saved_path)

        # Create ClonedVoice record
        cloned_voice = ClonedVoice.objects.create(
            user=user,
            name=title,
            audio_file=saved_path,
            duration=duration,
            file_size=file_size,
            is_active=True
        )

        return JsonResponse({
            'success': True,
            'voice_id': str(cloned_voice.id),
            'title': cloned_voice.name,
            'duration': cloned_voice.duration,
            'file_size': cloned_voice.file_size
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_http_methods(["GET"])
@login_required
def get_saved_voices(request):
    """
    Get list of user's saved reference voices
    Simple endpoint for clone.html UI
    """
    try:
        user = request.user
        voices = ClonedVoice.objects.filter(user=user, is_active=True).order_by('-created_at')

        data = []
        for v in voices:
            if v.audio_file:
                # Get relative URL and ensure it starts with /
                relative_url = v.audio_file.url
                if not relative_url.startswith('/'):
                    relative_url = '/' + relative_url

                # Build HTTPS URL directly
                url = f"https://{request.get_host()}{relative_url}"
            else:
                url = None

            data.append({
                'id': str(v.id),
                'title': v.name,
                'url': url,
                'duration': v.duration,
                'file_size': v.file_size,
                'created_at': v.created_at.strftime('%Y-%m-%d %H:%M:%S')
            })

        return JsonResponse({
            'success': True,
            'voices': data
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_http_methods(["GET"])
@login_required
def get_saved_voice_details(request, voice_id):
    """
    Get details of a specific saved voice
    """
    try:
        user = request.user
        voice = ClonedVoice.objects.get(id=voice_id, user=user, is_active=True)

        # Build HTTPS URL (auto-detect from request)
        url = None
        if voice.audio_file:
            # Get relative URL and ensure it starts with /
            relative_url = voice.audio_file.url
            if not relative_url.startswith('/'):
                relative_url = '/' + relative_url

            # Auto-detect HTTPS: check request.is_secure() OR domain name
            host = request.get_host()
            # Force HTTPS for talkstudio.ai domain
            if 'talkstudio.ai' in host:
                scheme = 'https'
            else:
                scheme = 'https' if request.is_secure() else request.scheme
            url = f"{scheme}://{host}{relative_url}"

        return JsonResponse({
            'success': True,
            'voice': {
                'id': str(voice.id),
                'title': voice.name,
                'url': url,
                'path': voice.audio_file.path if voice.audio_file else None,
                'duration': voice.duration,
                'file_size': voice.file_size,
                'created_at': voice.created_at.strftime('%Y-%m-%d %H:%M:%S')
            }
        })

    except ClonedVoice.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Voice not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


class DefaultVoiceManagementViewSet(viewsets.ModelViewSet):
    """Admin-only viewset for managing default voices in library"""
    serializer_class = VoiceLibrarySerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    queryset = VoiceLibrary.objects.all()

    def get_permissions(self):
        """Only admin/superadmin can access this"""
        if self.request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            # Check if user is admin or superadmin
            if not (self.request.user.is_staff or self.request.user.is_superuser):
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied("Only admins can manage default voices")
        return super().get_permissions()

    def list(self, request, *args, **kwargs):
        """List all default voices with error handling"""
        try:
            queryset = self.get_queryset()
            page = self.paginate_queryset(queryset)

            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)

            serializer = self.get_serializer(queryset, many=True)
            return Response({
                'results': serializer.data,
                'count': queryset.count()
            })
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error listing default voices: {str(e)}", exc_info=True)
            return Response({
                'results': [],
                'count': 0
            }, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        """Create a new default voice"""
        import logging
        logger = logging.getLogger(__name__)

        try:
            # Validate input
            name = request.data.get('name')
            gender = request.data.get('gender')
            accent = request.data.get('accent', '')
            language = request.data.get('language', 'English')
            description = request.data.get('description', '')
            voice_file = request.FILES.get('voice_file')
            image = request.FILES.get('image')
            preview_audio = request.FILES.get('preview_audio')

            if not name or not gender or not voice_file:
                return Response({
                    'error': 'Name, gender, and voice file are required'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Save voice file
            file_ext = os.path.splitext(voice_file.name)[1]
            filename = f"{uuid.uuid4()}{file_ext}"
            file_path = os.path.join(settings.MEDIA_ROOT, 'library_voices', filename)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            with open(file_path, 'wb+') as destination:
                for chunk in voice_file.chunks():
                    destination.write(chunk)

            # Save image if provided
            image_filename = None
            if image:
                try:
                    image_ext = os.path.splitext(image.name)[1]
                    image_filename = f"{uuid.uuid4()}{image_ext}"
                    image_path = os.path.join(settings.MEDIA_ROOT, 'library_images', image_filename)
                    os.makedirs(os.path.dirname(image_path), exist_ok=True)

                    with open(image_path, 'wb+') as destination:
                        for chunk in image.chunks():
                            destination.write(chunk)
                except Exception as e:
                    logger.warning(f"Error saving image: {e}")

            # Save preview audio if provided
            preview_filename = None
            if preview_audio:
                try:
                    preview_ext = os.path.splitext(preview_audio.name)[1]
                    preview_filename = f"{uuid.uuid4()}{preview_ext}"
                    preview_path = os.path.join(settings.MEDIA_ROOT, 'library_previews', preview_filename)
                    os.makedirs(os.path.dirname(preview_path), exist_ok=True)

                    with open(preview_path, 'wb+') as destination:
                        for chunk in preview_audio.chunks():
                            destination.write(chunk)
                except Exception as e:
                    logger.warning(f"Error saving preview audio: {e}")

            # Create VoiceLibrary record
            default_voice = VoiceLibrary.objects.create(
                name=name,
                gender=gender,
                accent=accent,
                language=language,
                description=description,
                voice_file=f"library_voices/{filename}",
                image=f"library_images/{image_filename}" if image_filename else None,
                preview_audio=f"library_previews/{preview_filename}" if preview_filename else None,
                is_active=True
            )

            return Response({
                'message': 'Default voice added successfully',
                'voice': VoiceLibrarySerializer(default_voice).data
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Error creating default voice: {str(e)}", exc_info=True)
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def destroy(self, request, *args, **kwargs):
        """Delete (deactivate) a default voice"""
        try:
            instance = self.get_object()
            instance.is_active = False
            instance.save()
            return Response({
                'message': 'Default voice deactivated successfully'
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
