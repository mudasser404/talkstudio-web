"""
WSGI config for voice_cloning project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/wsgi/
"""

import os

# Apply compatibility patches BEFORE any Django imports
from voice_cloning.startup_patches import apply_all_patches
apply_all_patches()

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'voice_cloning.settings')

application = get_wsgi_application()
