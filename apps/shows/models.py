"""
CineBook — Shows Models
========================
Models: Show, ShowSeat

ShowSeat is the critical join table that tracks per-show seat availability.
It is the target of all concurrency-safe locking operations.

Key invariants (enforced at DB level via constraints + application level):
1. Each (show, seat) combination is unique — no duplicate ShowSeat rows.
2. A ShowSeat can only be LOCKED by one user at a time.
3. LOCKED status expires after SEAT_LOCK_MINUTES minutes (enforced lazily + via cron).
4. BOOKED status is terminal — cannot be changed back to AVAILABLE without a cancellation.
"""

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.movies.models import Movie
from apps.theaters.models import Screen


class Show(models.Model):
    """
    A specific screening of a movie on a screen at a given date and time.
    A Show spans exactly one screen for exactly one movie.
    """

    movie = models.ForeignKey(
        Movie,
        on_delete=models.PROTECT,
        related_name="shows",
        verbose_name=_("Movie"),
    )
    screen = models.ForeignKey(
        Screen,
        on_delete=models.PROTECT,
        related_name="shows",
        verbose_name=_("Screen"),
    )
    start_time = models.DateTimeField(
        _("Start Time"),
        db_index=True,
        help_text="Full datetime of when the show begins (timezone-aware).",
    )
    end_time = models.DateTimeField(
        _("End Time (calculated)"),
        help_text="Set automatically based on start_time + movie.duration_minutes.",
    )
    date = models.DateField(
        _("Show Date"),
        db_index=True,
        help_text="Denormalised date for efficient date-based filtering without truncating datetime.",
    )
    language = models.CharField(
        _("Language"),
        max_length=50,
        help_text="Override language (e.g. dubbed version differs from movie.language).",
    )
    format = models.CharField(
        _("Format"),
        max_length=50,
        blank=True,
        default="2D",
        help_text='Screen format, e.g. "2D", "IMAX", "4DX", "PXL", "LUXE".',
    )
    is_cancellable = models.BooleanField(
        _("Cancellation Allowed"),
        default=True,
        help_text="Whether this show allows ticket cancellation.",
    )
    is_active = models.BooleanField(
        _("Is Active"),
        default=True,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Show")
        verbose_name_plural = _("Shows")
        ordering = ["date", "start_time"]
        indexes = [
            models.Index(fields=["movie", "date", "is_active"]),
            models.Index(fields=["screen", "date"]),
            models.Index(fields=["date", "is_active"]),
        ]

    def __str__(self) -> str:
        return (
            f"{self.movie.title} @ {self.screen} "
            f"— {self.start_time.strftime('%d %b %Y, %I:%M %p')}"
        )

    def save(self, *args, **kwargs) -> None:
        """Auto-populate end_time and date from start_time."""
        if self.start_time:
            from datetime import timedelta
            self.end_time = self.start_time + timedelta(minutes=self.movie.duration_minutes)
            self.date = self.start_time.date()
        super().save(*args, **kwargs)

    @property
    def is_bookable(self) -> bool:
        """Returns True only if the show is in the future and active."""
        return self.is_active and self.start_time > timezone.now()


class ShowSeat(models.Model):
    """
    The core concurrency-critical join table.
    One row per (show, seat) combination — created in bulk when a Show is scheduled.

    Status lifecycle:
        AVAILABLE → LOCKED (by a user during checkout) → BOOKED (after payment)
        LOCKED → AVAILABLE (if lock expires or user cancels)
        BOOKED → AVAILABLE (after a confirmed booking is cancelled, if policy allows)
    """

    class StatusChoices(models.TextChoices):
        AVAILABLE = "AVAILABLE", _("Available")
        LOCKED = "LOCKED", _("Locked (in checkout)")
        BOOKED = "BOOKED", _("Booked")

    show = models.ForeignKey(
        Show,
        on_delete=models.CASCADE,
        related_name="show_seats",
        verbose_name=_("Show"),
    )
    seat = models.ForeignKey(
        "theaters.Seat",
        on_delete=models.PROTECT,
        related_name="show_seats",
        verbose_name=_("Seat"),
    )
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.AVAILABLE,
        db_index=True,
    )
    locked_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="locked_show_seats",
        verbose_name=_("Locked By"),
    )
    locked_at = models.DateTimeField(
        _("Locked At"),
        null=True,
        blank=True,
        db_index=True,     # Index for efficient expiry sweep queries
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Show Seat")
        verbose_name_plural = _("Show Seats")
        unique_together = [("show", "seat")]    # DB-level uniqueness guarantee
        indexes = [
            models.Index(fields=["show", "status"]),
            models.Index(fields=["locked_at", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.show} — Seat {self.seat.label} ({self.status})"

    @property
    def lock_expiry(self):
        """Return the datetime when this lock expires, or None if not locked."""
        if self.status == self.StatusChoices.LOCKED and self.locked_at:
            from datetime import timedelta
            return self.locked_at + timedelta(minutes=settings.SEAT_LOCK_MINUTES)
        return None

    @property
    def is_lock_expired(self) -> bool:
        """Returns True if this seat is LOCKED but the lock window has elapsed."""
        expiry = self.lock_expiry
        return expiry is not None and timezone.now() > expiry
