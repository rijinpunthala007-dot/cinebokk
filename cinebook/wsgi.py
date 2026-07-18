"""WSGI config for CineBook project."""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cinebook.settings")
application = get_wsgi_application()
