"""
CineBook — Showtime Refresh Service
=====================================
Render's free tier has no persistent process for django-crontab, so shows
seeded on the last deploy go stale as their dates slip into the past. This
module rolls them forward into a live [today, today+6] window so
now-showing movies always have bookable shows, without a redeploy.

Called from two places that must stay in lock-step:
- apps.shows.management.commands.refresh_showtimes (manual / build.sh)
- apps.shows.views.RefreshShowtimesView (external cron ping)
"""

import logging
from datetime import timedelta

from django.utils import timezone

from apps.shows.models import Show

logger = logging.getLogger("apps.shows.services")

ROLLING_WINDOW_DAYS = 7  # today .. today+6


def refresh_showtimes() -> int:
    """
    Roll every Show belonging to a currently-released movie into the current
    [today, today+6] window, preserving each show's time-of-day and its
    ordering relative to the other distinct show dates.

    Movie has no persisted `is_now_showing` flag — seed_movies.py only ever
    used that name as a transient, unsaved marker (release_date in the past =
    now showing, release_date in the future = upcoming; see its MOVIE_DATA).
    `release_date__lte=today` is the real, queryable equivalent.

    Idempotent: once a show's date already matches its target slot in the
    window, re-running maps it to the same date again — a fixed point. Safe
    to call as often as needed in a day.
    """
    today = timezone.localdate()

    shows = list(
        Show.objects.filter(movie__release_date__lte=today).select_related("movie")
    )
    if not shows:
        return 0

    distinct_dates = sorted({show.date for show in shows})
    date_map = {
        old_date: today + timedelta(days=index % ROLLING_WINDOW_DAYS)
        for index, old_date in enumerate(distinct_dates)
    }

    to_update = []
    for show in shows:
        new_date = date_map[show.date]
        if new_date == show.date:
            continue
        delta = new_date - show.date
        show.start_time = show.start_time + delta
        show.end_time = show.start_time + timedelta(minutes=show.movie.duration_minutes)
        show.date = new_date
        to_update.append(show)

    if to_update:
        Show.objects.bulk_update(to_update, ["start_time", "end_time", "date"])
        logger.info("Rolled %d show(s) forward into the current window.", len(to_update))

    return len(to_update)
