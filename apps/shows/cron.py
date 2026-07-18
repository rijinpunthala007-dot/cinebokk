"""
CineBook — Expired Seat Lock Sweeper
======================================
Called every minute by django-crontab.
Finds all ShowSeat rows with status=LOCKED whose locked_at has passed the
SEAT_LOCK_MINUTES threshold, and resets them to AVAILABLE.

This is intentionally a bulk UPDATE — not individual row saves — to be
efficient even under high load. It does not trigger Django signals.
"""

import logging
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger("apps.shows.cron")


def release_expired_locks() -> int:
    """
    Release all expired ShowSeat locks in a single bulk UPDATE.

    Returns:
        The number of seat locks released.

    This function is intentionally Celery-free.
    It's registered in settings.CRONJOBS to run every minute.
    """
    # Import here to avoid circular imports at module load time
    from apps.shows.models import ShowSeat

    lock_minutes: int = getattr(settings, "SEAT_LOCK_MINUTES", 5)
    expiry_threshold = timezone.now() - timedelta(minutes=lock_minutes)

    released_count = ShowSeat.objects.filter(
        status=ShowSeat.StatusChoices.LOCKED,
        locked_at__lt=expiry_threshold,
    ).update(
        status=ShowSeat.StatusChoices.AVAILABLE,
        locked_by=None,
        locked_at=None,
    )

    if released_count > 0:
        logger.info(
            "Released %d expired seat lock(s) (threshold: %s minutes).",
            released_count,
            lock_minutes,
        )

    return released_count
