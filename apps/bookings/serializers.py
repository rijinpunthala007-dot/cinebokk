"""
CineBook — Bookings Serializers
================================
"""

from decimal import Decimal
import uuid

from rest_framework import serializers

from apps.shows.models import ShowSeat
from .models import Booking, BookingSeat


class LockSeatsRequestSerializer(serializers.Serializer):
    """Input validation for the lock-seats endpoint."""

    show_id = serializers.IntegerField(min_value=1)
    seat_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        min_length=1,
        max_length=10,
        allow_empty=False,
    )

    def validate_seat_ids(self, value: list[int]) -> list[int]:
        if len(value) != len(set(value)):
            raise serializers.ValidationError("Duplicate seat IDs are not allowed.")
        return value


class PaymentDataSerializer(serializers.Serializer):
    """Mock payment data — validated before sending to the gateway."""

    card_number = serializers.CharField(
        min_length=13,
        max_length=19,
        help_text="Card number, digits only (spaces stripped).",
    )
    expiry = serializers.CharField(
        min_length=4,
        max_length=7,
        help_text="Expiry in MM/YY or MM/YYYY format.",
    )
    cvv = serializers.CharField(min_length=3, max_length=4)
    name_on_card = serializers.CharField(min_length=2, max_length=200)

    def validate_card_number(self, value: str) -> str:
        cleaned = value.replace(" ", "").replace("-", "")
        if not cleaned.isdigit():
            raise serializers.ValidationError("Card number must contain only digits.")
        return cleaned


class ConfirmBookingRequestSerializer(serializers.Serializer):
    """Input validation for the booking confirmation endpoint."""

    show_id = serializers.IntegerField(min_value=1)
    seat_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        min_length=1,
        max_length=10,
        allow_empty=False,
    )
    payment = PaymentDataSerializer()


class BookingSeatSerializer(serializers.ModelSerializer):
    seat_label = serializers.CharField(source="seat.label", read_only=True)
    seat_row = serializers.CharField(source="seat.row_label", read_only=True)
    seat_number = serializers.IntegerField(source="seat.seat_number", read_only=True)
    category = serializers.CharField(source="seat.category.category", read_only=True)

    class Meta:
        model = BookingSeat
        fields = ["seat_label", "seat_row", "seat_number", "category", "price_at_booking"]


class BookingSerializer(serializers.ModelSerializer):
    """Full booking serializer — used in My Bookings and Confirmation page."""

    booking_seats = BookingSeatSerializer(many=True, read_only=True)
    movie_title = serializers.CharField(source="show.movie.title", read_only=True)
    # Poster served from /static/img/ (WhiteNoise) via stored poster_url, not the
    # MEDIA-served ImageField, so it survives Render's ephemeral disk.
    movie_poster = serializers.CharField(source="show.movie.poster_url", read_only=True)
    show_start_time = serializers.DateTimeField(source="show.start_time", read_only=True)
    theater_name = serializers.CharField(source="show.screen.theater.name", read_only=True)
    theater_city = serializers.CharField(source="show.screen.theater.city", read_only=True)
    screen_name = serializers.CharField(source="show.screen.name", read_only=True)
    booking_ref = serializers.UUIDField(read_only=True)

    class Meta:
        model = Booking
        fields = [
            "booking_ref", "status", "total_amount", "payment_ref",
            "booked_at", "created_at",
            "movie_title", "movie_poster", "show_start_time",
            "theater_name", "theater_city", "screen_name",
            "booking_seats",
        ]
        read_only_fields = fields


class CancelBookingRequestSerializer(serializers.Serializer):
    """Input validation for the cancellation endpoint."""

    reason = serializers.CharField(
        required=False,
        default="Cancelled by customer",
        max_length=500,
    )
