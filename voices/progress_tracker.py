"""Progress tracking for voice generation"""
from django.utils import timezone
from .models import GeneratedAudio

class VoiceGenerationTracker:
    SECONDS_PER_CHAR = 5.4  # Based on: 217s / 40 chars

    @classmethod
    def estimate_time(cls, text_length):
        return int(30 + (text_length * cls.SECONDS_PER_CHAR))

    @classmethod
    def create_task(cls, user, text, **kwargs):
        return GeneratedAudio.objects.create(
            user=user, text=text,
            characters_used=len(text),
            credits_used=len(text),
            status='pending',
            estimated_time=cls.estimate_time(len(text)),
            **kwargs
        )

    @classmethod
    def start_processing(cls, task_id):
        GeneratedAudio.objects.filter(id=task_id).update(
            status='processing', started_at=timezone.now(), progress=10
        )

    @classmethod
    def update_progress(cls, task_id, progress):
        GeneratedAudio.objects.filter(id=task_id).update(progress=min(progress, 99))

    @classmethod
    def mark_completed(cls, task_id, audio_file, file_size, duration):
        GeneratedAudio.objects.filter(id=task_id).update(
            status='completed', progress=100, completed_at=timezone.now(),
            audio_file=audio_file, file_size=file_size, duration=duration
        )

    @classmethod
    def mark_failed(cls, task_id, error):
        GeneratedAudio.objects.filter(id=task_id).update(
            status='failed', completed_at=timezone.now(), error_message=error
        )

    @classmethod
    def get_queue_position(cls, task_id):
        """Calculate queue position for a task"""
        try:
            task = GeneratedAudio.objects.get(id=task_id)

            # If task is already processing or completed, no queue
            if task.status in ['processing', 'completed', 'failed']:
                return 0

            # Count pending tasks created before this task
            queue_position = GeneratedAudio.objects.filter(
                status='pending',
                created_at__lt=task.created_at
            ).count()

            # Add 1 if there's a task currently processing
            processing_count = GeneratedAudio.objects.filter(status='processing').count()

            return queue_position + processing_count
        except:
            return 0

    @classmethod
    def get_status(cls, task_id):
        try:
            task = GeneratedAudio.objects.get(id=task_id)
            elapsed = int((timezone.now() - task.started_at).total_seconds()) if task.started_at else None
            remaining = max(0, task.estimated_time - elapsed) if task.estimated_time and elapsed else task.estimated_time

            # Get queue position
            queue_position = cls.get_queue_position(task_id)

            # Calculate estimated wait time if in queue
            estimated_wait = 0
            if queue_position > 0:
                # Average generation time: ~30 seconds
                estimated_wait = queue_position * 30

            return {
                'success': True,
                'status': task.status,
                'progress': task.progress,
                'estimated_time': task.estimated_time,
                'remaining_time': remaining,
                'audio_url': task.audio_file.url if task.audio_file else None,
                'queue_position': queue_position,
                'estimated_wait': estimated_wait,
            }
        except:
            return {'success': False, 'error': 'Not found'}
