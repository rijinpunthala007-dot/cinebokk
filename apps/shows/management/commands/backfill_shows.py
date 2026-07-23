"""
CineBook — Backfill Shows for Movies Missing Showtimes
========================================================
One-off idempotent command that creates Show + ShowSeat records for movies
that currently have no shows. Uses the same theater/time/format rotation as
the original seed_movies._create_shows(), spread across today → today+6.

Usage:
    python manage.py backfill_shows
"""

import logging
from datetime import date, time, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.movies.models import Movie
from apps.shows.models import Show, ShowSeat
from apps.theaters.models import Screen, Seat

logger = logging.getLogger("management")


class Command(BaseCommand):
    help = (
        "Create Show + ShowSeat records for movies that currently have no shows. "
        "Idempotent — skips movies that already have shows."
    )

    def handle(self, *args, **options):
        # Movies that have zero shows
        movies_needing_shows = list(
            Movie.objects.filter(is_active=True)
            .exclude(shows__isnull=False)
            .distinct()
        )

        if not movies_needing_shows:
            self.stdout.write(self.style.NOTICE(
                "All movies already have shows — nothing to backfill."
            ))
            return

        screens = list(
            Screen.objects.select_related("theater", "theater__city").all()
        )
        if not screens:
            self.stdout.write(self.style.WARNING("No screens found — cannot create shows."))
            return

        # Same patterns as seed_movies._create_shows()
        show_times = [time(10, 30), time(13, 45), time(17, 0), time(20, 15), time(22, 30)]
        formats = ["IMAX", "4K LASER DOLBY 7.1", "4DX", "PXL", "LUXE", "2D"]

        shows_created = 0
        seats_created = 0
        today = date.today()

        for day_offset in range(7):  # today → today+6
            show_date = today + timedelta(days=day_offset)

            for s_idx, screen in enumerate(screens):
                for m_step in range(3):
                    movie = movies_needing_shows[
                        (s_idx * 3 + m_step + day_offset * 5) % len(movies_needing_shows)
                    ]
                    t_idx = (s_idx + m_step + day_offset) % len(show_times)
                    show_time = show_times[t_idx]
                    start_dt = timezone.make_aware(
                        timezone.datetime.combine(show_date, show_time)
                    )

                    fmt = formats[(s_idx + t_idx) % len(formats)]
                    cancellation = (s_idx + t_idx) % 2 == 0

                    show, created = Show.objects.get_or_create(
                        movie=movie,
                        screen=screen,
                        start_time=start_dt,
                        defaults={
                            "end_time": start_dt + timedelta(minutes=movie.duration_minutes),
                            "date": show_date,
                            "language": movie.language,
                            "format": fmt,
                            "is_cancellable": cancellation,
                            "is_active": True,
                        },
                    )

                    if created:
                        shows_created += 1
                        seats = Seat.objects.filter(screen=screen)
                        show_seats = [
                            ShowSeat(
                                show=show,
                                seat=seat,
                                status=ShowSeat.StatusChoices.AVAILABLE,
                            )
                            for seat in seats
                        ]
                        ShowSeat.objects.bulk_create(show_seats, ignore_conflicts=True)
                        seats_created += len(show_seats)

        self.stdout.write(self.style.SUCCESS(
            f"  + Backfilled {shows_created} shows ({seats_created} show-seats) "
            f"for {len(movies_needing_shows)} movie(s) across {today} → "
            f"{today + timedelta(days=6)}"
        ))
