"""
CineBook — Shows App Configuration
"""

from django.apps import AppConfig


class ShowsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.shows"
    verbose_name = "Shows & Scheduling"
