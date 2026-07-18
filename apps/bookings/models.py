"""
CineBook — Bookings Models
===========================
Models: Booking, BookingSeat

A Booking is created atomically with its BookingSeat records only after
successful payment confirmation. The ShowSeat records are updated to BOOKED
status in the same atomic transaction.

booking_ref: a UUID that serves as the public-facing booking ID.
             Never expose internal integer PKs to users.
"""

import uuid
from decimal import Decimal

from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.shows.models import Show, ShowSeat
from apps.theaters.models import Seat


class Booking(models.Model):
    """
    A confirmed (or pending/cancelled) booking for a set of seats at a show.
    """

    class StatusChoices(models.TextChoices):
        PENDING = "PENDING", _("Pending Payment")
        CONFIRMED = "CONFIRMED", _("Confirmed")
        CANCELLED = "CANCELLED", _("Cancelled")
        EXPIRED = "EXPIRED", _("Expired (lock timed out)")

    customer = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="bookings",
        verbose_name=_("Customer"),
    )
    show = models.ForeignKey(
        Show,
        on_delete=models.PROTECT,
        related_name="bookings",
        verbose_name=_("Show"),
    )
    booking_ref = models.UUIDField(
        _("Booking Reference"),
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True,
        help_text="Public-facing unique reference shown to the customer.",
    )
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.PENDING,
        db_index=True,
    )
    total_amount = models.DecimalField(
        _("Total Amount (INR)"),
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    payment_ref = models.CharField(
        _("Payment Reference"),
        max_length=255,
        blank=True,
        default="",
        help_text="Reference from the (mock) payment gateway.",
    )
    booked_at = models.DateTimeField(
        _("Booked At"),
        null=True,
        blank=True,
        help_text="Set when the booking is confirmed (after successful payment).",
    )
    cancellation_reason = models.TextField(
        _("Cancellation Reason"),
        blank=True,
        default="",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Booking")
        verbose_name_plural = _("Bookings")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["customer", "status"]),
            models.Index(fields=["show", "status"]),
            models.Index(fields=["booking_ref"]),
        ]

    def __str__(self) -> str:
        return f"Booking #{str(self.booking_ref)[:8].upper()} — {self.show.movie.title} ({self.status})"

    @property
    def seat_count(self) -> int:
        """Number of seats in this booking."""
        return self.booking_seats.count()


class BookingSeat(models.Model):
    """
    A join record tying one seat (ShowSeat) to one Booking.
    OneToOne on show_seat ensures a ShowSeat can only belong to one Booking.
    """

    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name="booking_seats",
        verbose_name=_("Booking"),
    )
    show_seat = models.OneToOneField(
        ShowSeat,
        on_delete=models.PROTECT,
        related_name="booking_seat",
        verbose_name=_("Show Seat"),
    )
    seat = models.ForeignKey(
        Seat,
        on_delete=models.PROTECT,
        related_name="booking_seats",
        verbose_name=_("Seat"),
    )
    price_at_booking = models.DecimalField(
        _("Price at Time of Booking (INR)"),
        max_digits=8,
        decimal_places=2,
        help_text="Snapshot of seat price at booking time — price may change later.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Booking Seat")
        verbose_name_plural = _("Booking Seats")

    def __str__(self) -> str:
        return f"{self.booking} — Seat {self.seat.label}"
