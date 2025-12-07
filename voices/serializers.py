from rest_framework import serializers
from .models import VoiceLibrary, ClonedVoice, GeneratedAudio, VoiceGenerationHistory


class VoiceLibrarySerializer(serializers.ModelSerializer):
    """Serializer for default voice library"""
    voice_file = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    def get_voice_file(self, obj):
        """Return HTTPS URL for voice file"""
        if obj.voice_file:
            request = self.context.get('request')
            if request:
                # Get file path - handle both full path and filename only
                file_path = str(obj.voice_file)

                # If just filename, prepend media path
                if not file_path.startswith('library_voices/') and not file_path.startswith('/'):
                    file_path = f"library_voices/{file_path}"

                # Build full URL
                relative_url = f"/media/{file_path}" if not file_path.startswith('/') else file_path

                # Auto-detect HTTPS: check request.is_secure() OR domain name
                host = request.get_host()
                # Force HTTPS for talkstudio.ai domain
                if 'talkstudio.ai' in host:
                    scheme = 'https'
                else:
                    scheme = 'https' if request.is_secure() else request.scheme

                return f"{scheme}://{host}{relative_url}"
            return obj.voice_file.url
        return None

    def get_image(self, obj):
        """Return HTTPS URL for image or default"""
        if obj.image:
            request = self.context.get('request')
            if request:
                relative_url = obj.image.url
                if not relative_url.startswith('/'):
                    relative_url = '/' + relative_url
                # Auto-detect HTTPS: check request.is_secure() OR domain name
                host = request.get_host()
                # Force HTTPS for talkstudio.ai domain
                if 'talkstudio.ai' in host:
                    scheme = 'https'
                else:
                    scheme = 'https' if request.is_secure() else request.scheme
                return f"{scheme}://{host}{relative_url}"
            return obj.image.url
        return None

    class Meta:
        model = VoiceLibrary
        fields = [
            'id', 'name', 'gender', 'accent', 'language',
            'description', 'voice_file', 'image', 'preview_audio', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ClonedVoiceSerializer(serializers.ModelSerializer):
    """Serializer for cloned voices"""
    user_email = serializers.EmailField(source='user.email', read_only=True)
    audio_file = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    def get_audio_file(self, obj):
        """Return HTTPS URL for audio file"""
        if obj.audio_file:
            request = self.context.get('request')
            if request:
                # Get file path - handle both full path and filename only
                file_path = str(obj.audio_file)

                # If just filename, prepend cloned_voices path
                if not file_path.startswith('cloned_voices/') and not file_path.startswith('/'):
                    file_path = f"cloned_voices/{file_path}"

                # Build full URL
                relative_url = f"/media/{file_path}" if not file_path.startswith('/') else file_path

                # Auto-detect HTTPS: check request.is_secure() OR domain name
                host = request.get_host()
                # Force HTTPS for talkstudio.ai domain
                if 'talkstudio.ai' in host:
                    scheme = 'https'
                else:
                    scheme = 'https' if request.is_secure() else request.scheme
                return f"{scheme}://{host}{relative_url}"
            return obj.audio_file.url
        return None

    def get_image(self, obj):
        """Return HTTPS URL for image or default"""
        if obj.image:
            request = self.context.get('request')
            if request:
                relative_url = obj.image.url
                if not relative_url.startswith('/'):
                    relative_url = '/' + relative_url
                # Auto-detect HTTPS: check request.is_secure() OR domain name
                host = request.get_host()
                # Force HTTPS for talkstudio.ai domain
                if 'talkstudio.ai' in host:
                    scheme = 'https'
                else:
                    scheme = 'https' if request.is_secure() else request.scheme
                return f"{scheme}://{host}{relative_url}"
            return obj.image.url
        return None

    class Meta:
        model = ClonedVoice
        fields = [
            'id', 'name', 'user_email', 'audio_file', 'image', 'duration',
            'file_size', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user_email', 'duration', 'file_size', 'created_at', 'updated_at']


class ClonedVoiceCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating cloned voices"""
    audio_file = serializers.FileField(required=True)
    image = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = ClonedVoice
        fields = ['name', 'audio_file', 'image']

    def validate_audio_file(self, value):
        """Validate audio file size and format"""
        from django.conf import settings
        import os

        # Check file size
        if value.size > settings.MAX_AUDIO_FILE_SIZE:
            raise serializers.ValidationError(
                f"File size exceeds maximum allowed size of {settings.MAX_AUDIO_FILE_SIZE / (1024*1024)}MB"
            )

        # Check file extension
        ext = os.path.splitext(value.name)[1].lower()
        if ext not in settings.ALLOWED_AUDIO_FORMATS:
            raise serializers.ValidationError(
                f"File format not supported. Allowed formats: {', '.join(settings.ALLOWED_AUDIO_FORMATS)}"
            )

        return value

    def validate_image(self, value):
        """Validate image file size and format"""
        if value:
            # Check file size (max 5MB)
            if value.size > 5 * 1024 * 1024:
                raise serializers.ValidationError("Image size exceeds maximum allowed size of 5MB")

            # Check file extension
            import os
            ext = os.path.splitext(value.name)[1].lower()
            if ext not in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                raise serializers.ValidationError("Image format not supported. Allowed formats: jpg, jpeg, png, gif, webp")

        return value


class GeneratedAudioSerializer(serializers.ModelSerializer):
    """Serializer for generated audio"""
    user_email = serializers.EmailField(source='user.email', read_only=True)
    library_voice_name = serializers.CharField(source='library_voice.name', read_only=True)
    cloned_voice_name = serializers.CharField(source='cloned_voice.name', read_only=True)
    audio_file = serializers.SerializerMethodField()

    def get_audio_file(self, obj):
        """Return HTTPS URL for audio file"""
        if obj.audio_file:
            request = self.context.get('request')
            if request:
                # Get relative URL and ensure it starts with /
                relative_url = obj.audio_file.url
                if not relative_url.startswith('/'):
                    relative_url = '/' + relative_url

                # Build HTTPS URL directly
                return f"https://{request.get_host()}{relative_url}"
            return obj.audio_file.url
        return None

    class Meta:
        model = GeneratedAudio
        fields = [
            'id', 'user_email', 'text', 'voice_source',
            'library_voice', 'library_voice_name',
            'cloned_voice', 'cloned_voice_name',
            'audio_file', 'speed', 'pitch', 'tone',
            'duration', 'file_size', 'characters_used',
            'credits_used', 'created_at', 'status', 'progress'
        ]
        read_only_fields = [
            'id', 'user_email', 'audio_file', 'duration',
            'file_size', 'characters_used', 'credits_used', 'created_at'
        ]


class GeneratedAudioCreateSerializer(serializers.Serializer):
    """Serializer for creating generated audio with Index-TTS2 support"""
    text = serializers.CharField(max_length=50000, required=True)
    voice_source = serializers.ChoiceField(choices=['library', 'cloned', 'upload'], required=True)
    library_voice_id = serializers.IntegerField(required=False, allow_null=True)
    cloned_voice_id = serializers.UUIDField(required=False, allow_null=True)
    prompt_audio = serializers.FileField(required=False, allow_null=True)

    # Index-TTS2 Emotion Control Parameters
    emo_control_method = serializers.IntegerField(default=0, min_value=0, max_value=3)
    emo_ref_audio = serializers.FileField(required=False, allow_null=True)
    emo_weight = serializers.FloatField(default=0.65, min_value=0.0, max_value=1.0)
    emo_vectors = serializers.ListField(
        child=serializers.FloatField(min_value=0.0, max_value=1.0),
        required=False,
        allow_null=True,
        min_length=8,
        max_length=8
    )
    emo_text = serializers.CharField(max_length=500, required=False, allow_null=True, allow_blank=True)

    # Index-TTS2 Advanced Parameters
    temperature = serializers.FloatField(default=0.8, min_value=0.1, max_value=2.0)
    top_p = serializers.FloatField(default=0.8, min_value=0.0, max_value=1.0)
    top_k = serializers.IntegerField(default=30, min_value=0, max_value=100)
    num_beams = serializers.IntegerField(default=3, min_value=1, max_value=10)
    repetition_penalty = serializers.FloatField(default=10.0, min_value=0.1, max_value=20.0)
    length_penalty = serializers.FloatField(default=0.0, min_value=-2.0, max_value=2.0)
    max_mel_tokens = serializers.IntegerField(default=1500, min_value=50, max_value=3000)
    max_tokens_per_segment = serializers.IntegerField(default=120, min_value=20, max_value=200)

    # Legacy parameters (for backwards compatibility)
    speed = serializers.FloatField(default=1.0, min_value=0.5, max_value=2.0)
    pitch = serializers.FloatField(default=1.0, min_value=0.5, max_value=2.0)
    tone = serializers.FloatField(default=1.0, min_value=0.5, max_value=2.0)

    def validate(self, data):
        """Validate that appropriate voice is selected"""
        voice_source = data['voice_source']

        if voice_source == 'library' and not data.get('library_voice_id'):
            raise serializers.ValidationError("library_voice_id is required when voice_source is 'library'")

        if voice_source == 'cloned' and not data.get('cloned_voice_id'):
            raise serializers.ValidationError("cloned_voice_id is required when voice_source is 'cloned'")

        if voice_source == 'upload' and not data.get('prompt_audio'):
            raise serializers.ValidationError("prompt_audio is required when voice_source is 'upload'")

        # Validate emotion control method parameters
        emo_method = data.get('emo_control_method', 0)
        if emo_method == 1 and not data.get('emo_ref_audio'):
            # Emotion from reference audio requires emo_ref_audio
            pass  # Optional, will use speaker audio if not provided
        elif emo_method == 2 and not data.get('emo_vectors'):
            raise serializers.ValidationError("emo_vectors is required when emo_control_method is 2")

        return data


class VoiceGenerationHistorySerializer(serializers.ModelSerializer):
    """Serializer for voice generation history"""
    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = VoiceGenerationHistory
        fields = [
            'id', 'user_email', 'generated_audio', 'status',
            'error_message', 'processing_time', 'created_at', 'completed_at'
        ]
        read_only_fields = ['id', 'created_at']
