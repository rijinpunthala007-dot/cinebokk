"""
CineBook — Theaters App Configuration
"""

from django.apps import AppConfig


class TheatersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.theaters"
    verbose_name = "Theaters & Screens"
