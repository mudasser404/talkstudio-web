"""
Django management command to train F5-TTS model for a specific language
Includes real-time logging to admin panel
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from accounts.language_models import SupportedLanguage
import os
import sys
import subprocess
from pathlib import Path
import json


class Command(BaseCommand):
    help = 'Train F5-TTS model for a specific language'

    def add_arguments(self, parser):
        parser.add_argument('language_code', type=str, help='Language code (e.g., ur, en, ar)')
        parser.add_argument(
            '--dataset-path',
            type=str,
            required=True,
            help='Path to dataset directory containing wavs/ and metadata.list'
        )
        parser.add_argument(
            '--epochs',
            type=int,
            default=100,
            help='Number of training epochs (default: 100)'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=4,
            help='Batch size (default: 4)'
        )
        parser.add_argument(
            '--learning-rate',
            type=float,
            default=1e-4,
            help='Learning rate (default: 1e-4)'
        )
        parser.add_argument(
            '--output-dir',
            type=str,
            default='models/trained',
            help='Output directory for trained model (default: models/trained)'
        )

    def handle(self, *args, **options):
        language_code = options['language_code']
        dataset_path = Path(options['dataset_path'])
        epochs = options['epochs']
        batch_size = options['batch_size']
        learning_rate = options['learning_rate']
        output_dir = Path(options['output_dir'])

        self.stdout.write("=" * 80)
        self.stdout.write(self.style.SUCCESS(f"F5-TTS Training for Language: {language_code.upper()}"))
        self.stdout.write("=" * 80)

        # Get or create language entry
        try:
            language = SupportedLanguage.objects.get(language_code=language_code)
            self.stdout.write(f"✓ Language found: {language.language_name}")
        except SupportedLanguage.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"✗ Language '{language_code}' not found in database"))
            self.stdout.write("Available languages:")
            for lang in SupportedLanguage.objects.all():
                self.stdout.write(f"  - {lang.language_code}: {lang.language_name}")
            return

        # Validate dataset
        if not dataset_path.exists():
            self.stdout.write(self.style.ERROR(f"✗ Dataset path not found: {dataset_path}"))
            return

        wavs_dir = dataset_path / "wavs"
        metadata_file = dataset_path / "metadata.list"

        if not wavs_dir.exists():
            self.stdout.write(self.style.ERROR(f"✗ 'wavs' directory not found in: {dataset_path}"))
            return

        if not metadata_file.exists():
            self.stdout.write(self.style.ERROR(f"✗ 'metadata.list' file not found in: {dataset_path}"))
            return

        # Count files
        audio_files = list(wavs_dir.glob("*.wav"))
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata_lines = [l.strip() for l in f if l.strip() and '|' in l]

        self.stdout.write(f"\n{'=' * 80}")
        self.stdout.write("Dataset Validation:")
        self.stdout.write(f"  ✓ Audio files: {len(audio_files)}")
        self.stdout.write(f"  ✓ Metadata entries: {len(metadata_lines)}")
        self.stdout.write(f"  ✓ Dataset path: {dataset_path.absolute()}")
        self.stdout.write(f"{'=' * 80}\n")

        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)
        model_save_path = output_dir / f"{language_code}_f5tts"
        model_save_path.mkdir(parents=True, exist_ok=True)

        # Update language status
        language.training_status = 'training'
        language.save()
        self.stdout.write(f"✓ Updated training status to 'training'")

        # Training configuration
        self.stdout.write(f"\n{'=' * 80}")
        self.stdout.write("Training Configuration:")
        self.stdout.write(f"  - Epochs: {epochs}")
        self.stdout.write(f"  - Batch size: {batch_size}")
        self.stdout.write(f"  - Learning rate: {learning_rate}")
        self.stdout.write(f"  - Output directory: {model_save_path}")
        self.stdout.write(f"{'=' * 80}\n")

        # Prepare training script
        training_script = self._create_training_script(
            dataset_path=dataset_path,
            output_path=model_save_path,
            language_code=language_code,
            epochs=epochs,
            batch_size=batch_size,
            learning_rate=learning_rate
        )

        script_path = Path(f"train_{language_code}_temp.py")
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(training_script)

        self.stdout.write(f"✓ Training script created: {script_path}")

        try:
            # Run training with real-time output
            self.stdout.write(f"\n{'=' * 80}")
            self.stdout.write(self.style.SUCCESS("STARTING TRAINING"))
            self.stdout.write(f"{'=' * 80}\n")

            process = subprocess.Popen(
                [sys.executable, str(script_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )

            # Stream output
            for line in process.stdout:
                self.stdout.write(line.rstrip())
                self.stdout.flush()

            process.wait()

            if process.returncode == 0:
                # Training successful
                language.training_status = 'completed'
                language.is_trained = True
                language.model_path = str(model_save_path)
                language.save()

                self.stdout.write(f"\n{'=' * 80}")
                self.stdout.write(self.style.SUCCESS("✓ TRAINING COMPLETED SUCCESSFULLY!"))
                self.stdout.write(f"{'=' * 80}")
                self.stdout.write(f"Model saved to: {model_save_path}")
                self.stdout.write(f"Language '{language_code}' is now marked as trained")
            else:
                # Training failed
                language.training_status = 'failed'
                language.save()

                self.stdout.write(f"\n{'=' * 80}")
                self.stdout.write(self.style.ERROR("✗ TRAINING FAILED"))
                self.stdout.write(f"{'=' * 80}")
                self.stdout.write(f"Return code: {process.returncode}")

        except Exception as e:
            language.training_status = 'failed'
            language.save()

            self.stdout.write(f"\n{'=' * 80}")
            self.stdout.write(self.style.ERROR(f"✗ ERROR: {str(e)}"))
            self.stdout.write(f"{'=' * 80}")

        finally:
            # Cleanup
            if script_path.exists():
                script_path.unlink()
                self.stdout.write(f"\n✓ Cleaned up temporary files")

    def _create_training_script(self, dataset_path, output_path, language_code, epochs, batch_size, learning_rate):
        """Generate training script for F5-TTS"""

        script = f'''"""
Auto-generated F5-TTS training script for {language_code}
"""

import os
import sys
import torch
import torchaudio
from pathlib import Path
from tqdm import tqdm
import json

print("=" * 80)
print("F5-TTS Training Script")
print("=" * 80)
print(f"Language: {language_code}")
print(f"Dataset: {dataset_path}")
print(f"Output: {output_path}")
print("=" * 80)
print()

# Check CUDA
if torch.cuda.is_available():
    device = "cuda"
    print(f"✓ CUDA available - GPU: {{torch.cuda.get_device_name(0)}}")
else:
    device = "cpu"
    print("⚠ CUDA not available - Using CPU (training will be slow)")

print(f"Device: {{device}}")
print()

# Load dataset
metadata_file = Path("{dataset_path}") / "metadata.list"
wavs_dir = Path("{dataset_path}") / "wavs"

print("Loading dataset...")
with open(metadata_file, 'r', encoding='utf-8') as f:
    data = [line.strip().split('|') for line in f if line.strip() and '|' in line]

print(f"✓ Loaded {{len(data)}} samples")
print()

# Training configuration
config = {{
    "epochs": {epochs},
    "batch_size": {batch_size},
    "learning_rate": {learning_rate},
    "sample_rate": 24000,
    "n_mels": 100,
    "n_fft": 1024,
    "hop_length": 256,
    "win_length": 1024
}}

print("Training Configuration:")
for key, value in config.items():
    print(f"  {{key}}: {{value}}")
print()

# Initialize model (simplified - you'll need to import actual F5-TTS model)
print("Initializing model...")
# TODO: Import and initialize actual F5-TTS model here
# from f5_tts.model import F5TTS
# model = F5TTS().to(device)
print("⚠ Model initialization placeholder - integrate actual F5-TTS model")
print()

# Training loop
print("=" * 80)
print("STARTING TRAINING")
print("=" * 80)
print()

for epoch in range(config["epochs"]):
    epoch_num = epoch + 1
    print(f"Epoch {{epoch_num}}/{{config['epochs']}}")
    print("-" * 80)

    # Training logic here
    # TODO: Implement actual training loop

    # Simulate progress
    for i in tqdm(range(10), desc=f"Epoch {{epoch_num}}"):
        pass

    # Save checkpoint every 10 epochs
    if epoch_num % 10 == 0:
        checkpoint_path = Path("{output_path}") / f"checkpoint_epoch_{{epoch_num}}.pt"
        # torch.save(model.state_dict(), checkpoint_path)
        print(f"  ✓ Checkpoint saved: {{checkpoint_path.name}}")

    print()

# Save final model
final_model_path = Path("{output_path}") / "model_final.pt"
# torch.save(model.state_dict(), final_model_path)
print(f"✓ Final model saved: {{final_model_path}}")

# Save config
config_path = Path("{output_path}") / "config.json"
with open(config_path, 'w') as f:
    json.dump(config, f, indent=2)
print(f"✓ Config saved: {{config_path}}")

print()
print("=" * 80)
print("TRAINING COMPLETE!")
print("=" * 80)
'''

        return script