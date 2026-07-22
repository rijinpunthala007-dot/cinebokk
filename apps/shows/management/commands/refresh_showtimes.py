"""
CineBook — Refresh Showtimes Command
=======================================
Rolls currently-released movies' shows forward into the current
[today, today+6] window. See apps.shows.services.refresh_showtimes for the
shared logic also used by the /api/v1/internal/refresh-showtimes/ endpoint.

Usage:
    python manage.py refresh_showtimes
"""

from django.core.management.base import BaseCommand

from apps.shows.services import refresh_showtimes


class Command(BaseCommand):
    help = "Roll now-showing movies' shows forward into the current 7-day window."

    def handle(self, *args, **options):
        updated = refresh_showtimes()
        self.stdout.write(self.style.SUCCESS(f"  + {updated} show(s) rolled forward"))
