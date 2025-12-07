# voice_cloning/voice_cloning/__init__.py

from .celery import app as celery_app  # ← YEH SAHI HAI

__all__ = ("celery_app",)