from django.core.management.base import BaseCommand
from tts_engine.models import get_tts_model

class Command(BaseCommand):
    help = 'Preload Index-TTS2 model into memory'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Preloading Index-TTS2 model...'))
        self.stdout.write('This may take 1-2 minutes. Please wait...')
        self.stdout.write('')
        
        try:
            model = get_tts_model()
            
            if model and model.model_loaded:
                self.stdout.write(self.style.SUCCESS('✓ Model preloaded successfully!'))
                self.stdout.write('')
                self.stdout.write('Model is ready for voice generation.')
                self.stdout.write('You can now start the Django server.')
            else:
                self.stdout.write(self.style.ERROR('✗ Failed to load model'))
                self.stdout.write('')
                self.stdout.write('Check if model files exist in: checkpoints/')
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Error: {str(e)}'))
            self.stdout.write('')
            self.stdout.write('Please check server logs for details.')
