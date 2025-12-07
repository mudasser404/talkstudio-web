"""
Image and Video Compression Utilities
Automatically compress media files on upload
"""
import os
import logging
from io import BytesIO
from PIL import Image
from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)


def compress_image(image_file, quality=85, max_width=1920, max_height=1080):
    """
    Compress image file

    Args:
        image_file: Django UploadedFile object
        quality: JPEG quality (1-100)
        max_width: Maximum width
        max_height: Maximum height

    Returns:
        ContentFile with compressed image
    """
    try:
        # Open image
        img = Image.open(image_file)

        # Convert RGBA to RGB if necessary
        if img.mode in ('RGBA', 'LA', 'P'):
            # Create white background
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background

        # Resize if larger than max dimensions
        if img.width > max_width or img.height > max_height:
            img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
            logger.info(f"Resized image from original size to {img.width}x{img.height}")

        # Save to BytesIO
        output = BytesIO()
        img.save(output, format='JPEG', quality=quality, optimize=True)
        output.seek(0)

        # Get original filename without extension
        original_name = os.path.splitext(image_file.name)[0]
        compressed_name = f"{original_name}_compressed.jpg"

        logger.info(f"Compressed image: {image_file.name} -> {compressed_name}")

        return ContentFile(output.read(), name=compressed_name)

    except Exception as e:
        logger.error(f"Image compression failed: {e}")
        # Return original file if compression fails
        return image_file


def compress_video(video_file, target_size_mb=50):
    """
    Compress video file using ffmpeg

    Args:
        video_file: Django UploadedFile object
        target_size_mb: Target size in MB

    Returns:
        ContentFile with compressed video or original if ffmpeg not available
    """
    try:
        import subprocess
        import tempfile

        # Create temp files
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_input:
            # Save uploaded video to temp file
            for chunk in video_file.chunks():
                tmp_input.write(chunk)
            input_path = tmp_input.name

        output_path = input_path.replace('.mp4', '_compressed.mp4')

        # Get video duration for bitrate calculation
        duration_cmd = [
            'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1', input_path
        ]

        try:
            duration = float(subprocess.check_output(duration_cmd).decode().strip())
            # Calculate bitrate: (target_size_mb * 8192) / duration
            target_bitrate = int((target_size_mb * 8192) / duration)
            target_bitrate = f"{target_bitrate}k"
        except:
            # Default bitrate if duration detection fails
            target_bitrate = "2M"

        # Compress video with ffmpeg
        cmd = [
            'ffmpeg', '-i', input_path,
            '-c:v', 'libx264',  # H.264 codec
            '-b:v', target_bitrate,  # Video bitrate
            '-c:a', 'aac',  # Audio codec
            '-b:a', '128k',  # Audio bitrate
            '-preset', 'medium',  # Compression preset
            '-movflags', '+faststart',  # Web optimization
            '-y',  # Overwrite output
            output_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0 and os.path.exists(output_path):
            # Read compressed video
            with open(output_path, 'rb') as f:
                compressed_data = f.read()

            # Cleanup temp files
            os.unlink(input_path)
            os.unlink(output_path)

            original_name = os.path.splitext(video_file.name)[0]
            compressed_name = f"{original_name}_compressed.mp4"

            original_size = video_file.size / (1024 * 1024)  # MB
            compressed_size = len(compressed_data) / (1024 * 1024)  # MB

            logger.info(f"Compressed video: {original_size:.2f}MB -> {compressed_size:.2f}MB")

            return ContentFile(compressed_data, name=compressed_name)
        else:
            logger.error(f"ffmpeg compression failed: {result.stderr}")
            os.unlink(input_path)
            return video_file

    except ImportError:
        logger.warning("ffmpeg not available, skipping video compression")
        return video_file
    except Exception as e:
        logger.error(f"Video compression failed: {e}")
        return video_file


def get_file_size_mb(file_obj):
    """Get file size in MB"""
    if hasattr(file_obj, 'size'):
        return file_obj.size / (1024 * 1024)
    return 0