"""
TTS API Service for Voice Cloning
External API integration for voice generation (replaces local model)
"""

import os
import logging
import uuid
import tempfile
import base64
import requests
from pathlib import Path
from typing import Dict, Any, Optional
from django.conf import settings

logger = logging.getLogger(__name__)


class TTSAPIService:
    """
    TTS API Service for voice cloning
    Calls external API instead of local model
    """

    def __init__(self):
        """Initialize TTS API Service"""
        # API Configuration - set these in Django settings or environment
        self.api_url = getattr(settings, 'TTS_API_URL', os.environ.get('TTS_API_URL', ''))
        self.api_key = getattr(settings, 'TTS_API_KEY', os.environ.get('TTS_API_KEY', ''))
        self.api_timeout = getattr(settings, 'TTS_API_TIMEOUT', 300)  # 5 minutes default

        # Service status
        self.is_available = bool(self.api_url)

        if self.is_available:
            logger.info(f"TTS API Service initialized - URL: {self.api_url[:50]}...")
        else:
            logger.warning("TTS API Service not configured - Set TTS_API_URL in settings")

    def _encode_audio_base64(self, audio_path: str) -> Optional[str]:
        """Encode audio file to base64 string"""
        try:
            with open(audio_path, 'rb') as f:
                return base64.b64encode(f.read()).decode('utf-8')
        except Exception as e:
            logger.error(f"Error encoding audio: {e}")
            return None

    def _decode_audio_base64(self, audio_data: str, output_path: str) -> bool:
        """Decode base64 audio and save to file"""
        try:
            audio_bytes = base64.b64decode(audio_data)
            with open(output_path, 'wb') as f:
                f.write(audio_bytes)
            return True
        except Exception as e:
            logger.error(f"Error decoding audio: {e}")
            return False

    def generate(
        self,
        text: str,
        reference_audio: str,
        reference_text: str = "",
        speed: float = 1.0,
        nfe_step: int = 32,
        cfg_strength: float = 2.0,
        sway_sampling_coef: float = -1.0,
        language: str = "multilingual",
        clean_audio: bool = True,
        noise_reduction_strength: float = 0.3,
        remove_silence: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate speech using external TTS API

        Args:
            text: Text to synthesize
            reference_audio: Path to reference audio file
            reference_text: Transcript of reference audio
            speed: Speed factor (default: 1.0)
            nfe_step: NFE steps (default: 32)
            cfg_strength: CFG strength (default: 2.0)
            sway_sampling_coef: Sway sampling coefficient (default: -1.0)
            language: Language code (default: multilingual)
            clean_audio: Whether to clean audio (default: True)
            noise_reduction_strength: Noise reduction strength (default: 0.3)
            remove_silence: Remove silence from output (default: False)

        Returns:
            Dictionary with generation results
        """
        if not self.is_available:
            return {
                'success': False,
                'error': 'TTS API not configured. Set TTS_API_URL in settings.'
            }

        # Validate reference audio exists
        if not os.path.exists(reference_audio):
            return {
                'success': False,
                'error': f'Reference audio not found: {reference_audio}'
            }

        # Validate audio file size
        try:
            file_size = os.path.getsize(reference_audio)
            if file_size == 0:
                return {
                    'success': False,
                    'error': 'Reference audio file is empty'
                }
            if file_size < 1000:
                return {
                    'success': False,
                    'error': 'Reference audio file too small. Please upload a longer audio sample.'
                }
        except Exception as e:
            return {
                'success': False,
                'error': f'Cannot read reference audio: {str(e)}'
            }

        try:
            logger.info(f"Calling TTS API for text: {text[:50]}...")
            logger.info(f"Parameters: speed={speed}, nfe_step={nfe_step}, language={language}")

            # Encode reference audio
            audio_base64 = self._encode_audio_base64(reference_audio)
            if not audio_base64:
                return {
                    'success': False,
                    'error': 'Failed to encode reference audio'
                }

            # Prepare API request payload
            payload = {
                'text': text,
                'reference_audio': audio_base64,
                'reference_text': reference_text,
                'speed': speed,
                'nfe_step': nfe_step,
                'cfg_strength': cfg_strength,
                'sway_sampling_coef': sway_sampling_coef,
                'language': language,
                'clean_audio': clean_audio,
                'noise_reduction_strength': noise_reduction_strength,
                'remove_silence': remove_silence
            }

            # Prepare headers
            headers = {
                'Content-Type': 'application/json'
            }
            if self.api_key:
                headers['Authorization'] = f'Bearer {self.api_key}'

            # Make API request
            response = requests.post(
                self.api_url,
                json=payload,
                headers=headers,
                timeout=self.api_timeout
            )

            # Check response status
            if response.status_code != 200:
                error_msg = f"API returned status {response.status_code}"
                try:
                    error_data = response.json()
                    if 'error' in error_data:
                        error_msg = error_data['error']
                    elif 'message' in error_data:
                        error_msg = error_data['message']
                except:
                    error_msg = response.text[:200] if response.text else error_msg

                return {
                    'success': False,
                    'error': error_msg
                }

            # Parse response
            result = response.json()

            if not result.get('success', False):
                return {
                    'success': False,
                    'error': result.get('error', 'API returned unsuccessful response')
                }

            # Get audio data from response
            audio_data = result.get('audio_data') or result.get('audio')
            if not audio_data:
                return {
                    'success': False,
                    'error': 'No audio data in API response'
                }

            # Save audio to temp file
            output_path = os.path.join(
                tempfile.gettempdir(),
                f'tts_output_{uuid.uuid4().hex}.wav'
            )

            if not self._decode_audio_base64(audio_data, output_path):
                return {
                    'success': False,
                    'error': 'Failed to decode audio from API response'
                }

            # Get file info
            file_size = os.path.getsize(output_path)
            duration = result.get('duration', 0)

            # If duration not provided, calculate from file
            if not duration:
                try:
                    import soundfile as sf
                    data, sr = sf.read(output_path)
                    duration = len(data) / sr
                except:
                    duration = 0

            logger.info(f"TTS API generation successful: {output_path}")

            return {
                'success': True,
                'audio_path': output_path,
                'duration': duration,
                'file_size': file_size,
                'sample_rate': result.get('sample_rate', 24000),
                'characters_used': len(text),
                'language': language
            }

        except requests.exceptions.Timeout:
            return {
                'success': False,
                'error': f'API request timed out after {self.api_timeout} seconds'
            }
        except requests.exceptions.ConnectionError:
            return {
                'success': False,
                'error': 'Cannot connect to TTS API server'
            }
        except Exception as e:
            logger.error(f"TTS API error: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }

    def check_status(self) -> Dict[str, Any]:
        """Check API service status"""
        if not self.is_available:
            return {
                'available': False,
                'error': 'API not configured'
            }

        try:
            # Try to call health/status endpoint if available
            status_url = self.api_url.rstrip('/').rsplit('/', 1)[0] + '/status'
            headers = {}
            if self.api_key:
                headers['Authorization'] = f'Bearer {self.api_key}'

            response = requests.get(status_url, headers=headers, timeout=10)

            if response.status_code == 200:
                return {
                    'available': True,
                    'status': response.json()
                }
            else:
                # Status endpoint might not exist, but main API might still work
                return {
                    'available': True,
                    'status': 'API endpoint configured'
                }
        except:
            return {
                'available': self.is_available,
                'status': 'API endpoint configured (status check unavailable)'
            }


# Singleton instance
_tts_api_service = None


def get_tts_api_service() -> TTSAPIService:
    """Get or create TTSAPIService singleton instance"""
    global _tts_api_service
    if _tts_api_service is None:
        _tts_api_service = TTSAPIService()
    return _tts_api_service
