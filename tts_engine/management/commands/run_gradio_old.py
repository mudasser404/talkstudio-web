"""
Django Management Command to run Index-TTS Gradio Interface
This integrates the Gradio WebUI directly into Django
"""

import os
import sys
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Run the Index-TTS Gradio WebUI integrated with Django'

    def add_arguments(self, parser):
        parser.add_argument(
            '--port',
            type=int,
            default=7860,
            help='Port to run Gradio on (default: 7860)'
        )
        parser.add_argument(
            '--host',
            type=str,
            default='0.0.0.0',
            help='Host to bind Gradio to (default: 0.0.0.0)'
        )
        parser.add_argument(
            '--model_dir',
            type=str,
            default=None,
            help='Path to model checkpoints directory'
        )
        parser.add_argument(
            '--fp16',
            action='store_true',
            help='Use FP16 precision for faster inference'
        )
        parser.add_argument(
            '--share',
            action='store_true',
            help='Create a public Gradio share link'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Enable verbose logging'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting Index-TTS Gradio WebUI...'))

        # Get the project root (where index-tts folder is)
        project_root = Path(settings.BASE_DIR).parent
        index_tts_path = project_root / 'index-tts'

        if not index_tts_path.exists():
            self.stdout.write(
                self.style.ERROR(
                    f'index-tts directory not found at {index_tts_path}\n'
                    'Please ensure the index-tts folder is at the project root.'
                )
            )
            return

        # Set model directory
        if options['model_dir']:
            # Convert to absolute path to avoid HuggingFace validation errors
            model_dir = str(Path(options['model_dir']).resolve())
        else:
            # Try common locations
            # PRIORITY ORDER: Check voice_cloning/checkpoints FIRST (for deployment)
            possible_dirs = [
                Path(settings.BASE_DIR) / 'checkpoints',  # 1st: D:\VoiceCloning\voice_cloning\checkpoints
                project_root / 'checkpoints',              # 2nd: D:\VoiceCloning\checkpoints
                index_tts_path / 'checkpoints',            # 3rd: D:\VoiceCloning\index-tts\checkpoints (dev only)
            ]
            model_dir = None
            for dir_path in possible_dirs:
                if dir_path.exists() and (dir_path / 'config.yaml').exists():
                    # Convert to absolute path to avoid HuggingFace validation errors
                    model_dir = str(dir_path.resolve())
                    break

            if not model_dir:
                self.stdout.write(
                    self.style.ERROR(
                        'Model checkpoints not found. Please specify --model_dir or ensure '
                        'checkpoints exist in one of these locations:\n' +
                        '\n'.join(f'  - {d}' for d in possible_dirs)
                    )
                )
                return

        self.stdout.write(f'Using model directory: {model_dir}')

        # Add index-tts to Python path
        sys.path.insert(0, str(index_tts_path))

        # Change to index-tts directory (needed for relative imports)
        original_cwd = os.getcwd()
        os.chdir(str(index_tts_path))

        try:
            # Import and run the webui
            self.stdout.write('Loading Gradio interface...')

            # Set up arguments for webui
            sys.argv = [
                'webui.py',
                '--port', str(options['port']),
                '--host', options['host'],
                '--model_dir', model_dir,
            ]

            if options['fp16']:
                sys.argv.append('--fp16')

            if options['verbose']:
                sys.argv.append('--verbose')

            # Import webui module
            import webui

            # The webui.py file should start the Gradio server automatically
            # If it doesn't, we need to call the launch function

        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('\nShutting down Gradio server...'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error running Gradio: {e}'))
            import traceback
            traceback.print_exc()
        finally:
            # Restore original directory
            os.chdir(original_cwd)
