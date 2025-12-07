from django.core.management.base import BaseCommand
from accounts.language_models import SupportedLanguage


class Command(BaseCommand):
    help = 'Populate initial supported languages with default trained languages'

    def handle(self, *args, **kwargs):
        # Create or update the trained languages (English & Chinese)
        languages = [
            {
                'language_code': 'multilingual',
                'language_name': 'Auto-Detect',
                'native_name': 'Multilingual',
                'flag_emoji': '🌐',
                'is_enabled': True,
                'is_trained': True,
                'training_status': 'completed',
                'quality_score': 90.0,
                'description': 'Automatically detects between English and Chinese. Uses the default F5-TTS multilingual model.'
            },
            {
                'language_code': 'en',
                'language_name': 'English',
                'native_name': 'English',
                'flag_emoji': '🇬🇧',
                'is_enabled': True,
                'is_trained': True,
                'training_status': 'completed',
                'quality_score': 95.0,
                'description': 'Default F5-TTS model trained on English language with high quality.'
            },
            {
                'language_code': 'zh',
                'language_name': 'Chinese',
                'native_name': '中文',
                'flag_emoji': '🇨🇳',
                'is_enabled': True,
                'is_trained': True,
                'training_status': 'completed',
                'quality_score': 95.0,
                'description': 'Default F5-TTS model trained on Chinese (Mandarin) with high quality.'
            },
            # Add untrained languages that can be trained in the future
            {
                'language_code': 'es',
                'language_name': 'Spanish',
                'native_name': 'Español',
                'flag_emoji': '🇪🇸',
                'is_enabled': False,
                'is_trained': False,
                'training_status': 'not_started',
                'quality_score': 0.0,
                'description': 'Spanish language support - requires training'
            },
            {
                'language_code': 'fr',
                'language_name': 'French',
                'native_name': 'Français',
                'flag_emoji': '🇫🇷',
                'is_enabled': False,
                'is_trained': False,
                'training_status': 'not_started',
                'quality_score': 0.0,
                'description': 'French language support - requires training'
            },
            {
                'language_code': 'de',
                'language_name': 'German',
                'native_name': 'Deutsch',
                'flag_emoji': '🇩🇪',
                'is_enabled': False,
                'is_trained': False,
                'training_status': 'not_started',
                'quality_score': 0.0,
                'description': 'German language support - requires training'
            },
            {
                'language_code': 'it',
                'language_name': 'Italian',
                'native_name': 'Italiano',
                'flag_emoji': '🇮🇹',
                'is_enabled': False,
                'is_trained': False,
                'training_status': 'not_started',
                'quality_score': 0.0,
                'description': 'Italian language support - requires training'
            },
            {
                'language_code': 'ja',
                'language_name': 'Japanese',
                'native_name': '日本語',
                'flag_emoji': '🇯🇵',
                'is_enabled': False,
                'is_trained': False,
                'training_status': 'not_started',
                'quality_score': 0.0,
                'description': 'Japanese language support - requires training'
            },
            {
                'language_code': 'ru',
                'language_name': 'Russian',
                'native_name': 'Русский',
                'flag_emoji': '🇷🇺',
                'is_enabled': False,
                'is_trained': False,
                'training_status': 'not_started',
                'quality_score': 0.0,
                'description': 'Russian language support - requires training'
            },
            {
                'language_code': 'hi',
                'language_name': 'Hindi',
                'native_name': 'हिन्दी',
                'flag_emoji': '🇮🇳',
                'is_enabled': False,
                'is_trained': False,
                'training_status': 'not_started',
                'quality_score': 0.0,
                'description': 'Hindi language support - requires training'
            },
            {
                'language_code': 'ko',
                'language_name': 'Korean',
                'native_name': '한국어',
                'flag_emoji': '🇰🇷',
                'is_enabled': False,
                'is_trained': False,
                'training_status': 'not_started',
                'quality_score': 0.0,
                'description': 'Korean language support - requires training'
            },
            {
                'language_code': 'pt',
                'language_name': 'Portuguese',
                'native_name': 'Português',
                'flag_emoji': '🇵🇹',
                'is_enabled': False,
                'is_trained': False,
                'training_status': 'not_started',
                'quality_score': 0.0,
                'description': 'Portuguese language support - requires training'
            },
            {
                'language_code': 'ar',
                'language_name': 'Arabic',
                'native_name': 'العربية',
                'flag_emoji': '🇸🇦',
                'is_enabled': False,
                'is_trained': False,
                'training_status': 'not_started',
                'quality_score': 0.0,
                'description': 'Arabic language support - requires training'
            },
            {
                'language_code': 'tr',
                'language_name': 'Turkish',
                'native_name': 'Türkçe',
                'flag_emoji': '🇹🇷',
                'is_enabled': False,
                'is_trained': False,
                'training_status': 'not_started',
                'quality_score': 0.0,
                'description': 'Turkish language support - requires training'
            },
            {
                'language_code': 'nl',
                'language_name': 'Dutch',
                'native_name': 'Nederlands',
                'flag_emoji': '🇳🇱',
                'is_enabled': False,
                'is_trained': False,
                'training_status': 'not_started',
                'quality_score': 0.0,
                'description': 'Dutch language support - requires training'
            },
        ]

        created_count = 0
        updated_count = 0

        for lang_data in languages:
            language, created = SupportedLanguage.objects.update_or_create(
                language_code=lang_data['language_code'],
                defaults=lang_data
            )

            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created: {language.language_name} ({language.language_code})')
                )
            else:
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'Updated: {language.language_name} ({language.language_code})')
                )

        self.stdout.write(
            self.style.SUCCESS(f'\nSuccessfully populated languages: {created_count} created, {updated_count} updated')
        )
