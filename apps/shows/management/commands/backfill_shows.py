"""
CineBook — Backfill Shows (BookMyShow-style)
=============================================
Wipes all existing Show + ShowSeat records and creates a fresh, dense
showtime grid so every movie has shows across ALL 7 days, in EVERY theater,
with multiple showtimes per day — exactly like BookMyShow.

Each movie × each screen × each day gets 2–3 showtimes at different hours,
with format based on the screen name (IMAX screens get IMAX, 4DX screens
get 4DX, etc.).

Usage:
    python manage.py backfill_shows           # wipe & regenerate
    python manage.py backfill_shows --keep     # only add missing shows
"""

import logging
from datetime import date, time, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.movies.models import Movie
from apps.shows.models import Show, ShowSeat
from apps.theaters.models import Screen, Seat

logger = logging.getLogger("management")

# Showtime slots — each movie gets 2-3 per screen per day (rotated)
ALL_SLOTS = [
    time(10, 0),
    time(13, 15),
    time(16, 30),
    time(19, 45),
    time(22, 30),
]


def _screen_format(screen_name: str) -> str:
    """Derive a show format from the screen name, like BookMyShow does."""
    name_upper = screen_name.upper()
    if "IMAX" in name_upper:
        return "IMAX"
    if "4DX" in name_upper:
        return "4DX"
    if "PXL" in name_upper:
        return "PXL"
    if "LUXE" in name_upper:
        return "LUXE"
    if "DOLBY" in name_upper:
        return "4K LASER DOLBY 7.1"
    return "2D"


class Command(BaseCommand):
    help = (
        "Regenerate Show + ShowSeat records so every movie shows across "
        "all 7 days in every theater (BookMyShow-style dense schedule)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--keep",
            action="store_true",
            help="Keep existing shows and only add for movies/days/screens that are missing.",
        )

    def handle(self, *args, **options):
        keep = options["keep"]

        movies = list(Movie.objects.filter(is_active=True).order_by("pk"))
        screens = list(
            Screen.objects.select_related("theater", "theater__city")
            .prefetch_related("seats")
            .all()
        )

        if not movies:
            self.stdout.write(self.style.WARNING("No movies found."))
            return
        if not screens:
            self.stdout.write(self.style.WARNING("No screens found."))
            return

        if not keep:
            # Must clear bookings first — BookingSeat has a PROTECT FK to ShowSeat
            from apps.bookings.models import BookingSeat, Booking
            old_bseats = BookingSeat.objects.count()
            old_bookings = Booking.objects.count()
            BookingSeat.objects.all().delete()
            Booking.objects.all().delete()

            old_shows = Show.objects.count()
            old_seats = ShowSeat.objects.count()
            ShowSeat.objects.all().delete()
            Show.objects.all().delete()
            self.stdout.write(self.style.WARNING(
                f"  - Cleared {old_bookings} bookings, {old_bseats} booking-seats, "
                f"{old_shows} shows, {old_seats} show-seats."
            ))

        today = date.today()
        shows_created = 0
        seats_created = 0

        # For every movie, create shows at every screen for 7 days
        # Each movie gets 2-3 showtimes per screen per day (staggered by movie index)
        for m_idx, movie in enumerate(movies):
            for day_offset in range(7):
                show_date = today + timedelta(days=day_offset)

                for s_idx, screen in enumerate(screens):
                    fmt = _screen_format(screen.name)

                    # Each movie gets 2-3 slots per screen per day
                    # Stagger by movie index so not every movie plays at the same time
                    base = (m_idx + s_idx + day_offset) % len(ALL_SLOTS)
                    # Pick 2 or 3 slots depending on movie+screen combo
                    num_slots = 3 if (m_idx + s_idx) % 3 != 0 else 2
                    slot_indices = [(base + i * 2) % len(ALL_SLOTS) for i in range(num_slots)]

                    for si in slot_indices:
                        show_time = ALL_SLOTS[si]
                        start_dt = timezone.make_aware(
                            timezone.datetime.combine(show_date, show_time)
                        )

                        cancellation = (m_idx + s_idx + day_offset) % 2 == 0

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
                            screen_seats = Seat.objects.filter(screen=screen)
                            show_seats = [
                                ShowSeat(
                                    show=show,
                                    seat=seat,
                                    status=ShowSeat.StatusChoices.AVAILABLE,
                                )
                                for seat in screen_seats
                            ]
                            ShowSeat.objects.bulk_create(show_seats, ignore_conflicts=True)
                            seats_created += len(show_seats)

        self.stdout.write(self.style.SUCCESS(
            f"\n  [DONE] Created {shows_created} shows ({seats_created} show-seats)\n"
            f"    Movies:  {len(movies)}\n"
            f"    Screens: {len(screens)}\n"
            f"    Days:    {today} to {today + timedelta(days=6)}\n"
            f"    Pattern: 2-3 showtimes per movie per screen per day\n"
        ))
