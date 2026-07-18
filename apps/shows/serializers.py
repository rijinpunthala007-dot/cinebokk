"""
CineBook — Shows Serializers
=============================
"""

from rest_framework import serializers
from django.utils import timezone

from apps.movies.serializers import MovieListSerializer
from apps.theaters.models import Screen
from .models import Show, ShowSeat


class ScreenSerializer(serializers.ModelSerializer):
    theater_name = serializers.CharField(source="theater.name", read_only=True)
    theater_city = serializers.CharField(source="theater.city.name", read_only=True)

    class Meta:
        model = Screen
        fields = ["id", "name", "total_capacity", "theater_name", "theater_city"]


class ShowListSerializer(serializers.ModelSerializer):
    """Compact serializer for showtimes listing."""

    movie_title = serializers.CharField(source="movie.title", read_only=True)
    # Poster is served from /static/img/ (WhiteNoise) via the stored poster_url,
    # not the MEDIA-served ImageField, so it survives Render's ephemeral disk.
    movie_poster = serializers.CharField(source="movie.poster_url", read_only=True)
    screen_name = serializers.CharField(source="screen.name", read_only=True)
    theater_name = serializers.CharField(source="screen.theater.name", read_only=True)
    theater_city = serializers.CharField(source="screen.theater.city.name", read_only=True)
    theater_address = serializers.CharField(source="screen.theater.address", read_only=True)
    theater_amenities = serializers.JSONField(source="screen.theater.amenities", read_only=True)
    is_bookable = serializers.BooleanField(read_only=True)
    available_seats = serializers.SerializerMethodField()
    total_seats = serializers.SerializerMethodField()
    availability_pct = serializers.SerializerMethodField()

    class Meta:
        model = Show
        fields = [
            "id", "movie_title", "movie_poster", "screen_name", "theater_name",
            "theater_city", "theater_address", "theater_amenities",
            "start_time", "end_time", "date", "language", "format",
            "is_cancellable", "is_active", "is_bookable",
            "available_seats", "total_seats", "availability_pct",
        ]

    def get_available_seats(self, obj: Show) -> int:
        return obj.show_seats.filter(status=ShowSeat.StatusChoices.AVAILABLE).count()

    def get_total_seats(self, obj: Show) -> int:
        return obj.show_seats.count()

    def get_availability_pct(self, obj: Show) -> int:
        total = obj.show_seats.count()
        if total == 0:
            return 0
        available = obj.show_seats.filter(status=ShowSeat.StatusChoices.AVAILABLE).count()
        return round((available / total) * 100)


class ShowDetailSerializer(serializers.ModelSerializer):
    movie = MovieListSerializer(read_only=True)
    screen = ScreenSerializer(read_only=True)
    is_bookable = serializers.BooleanField(read_only=True)

    class Meta:
        model = Show
        fields = [
            "id", "movie", "screen", "start_time", "end_time", "date",
            "language", "is_active", "is_bookable",
        ]


class ShowSeatSerializer(serializers.ModelSerializer):
    """Serializer for individual seat status in the seat map."""

    seat_id = serializers.IntegerField(source="seat.id", read_only=True)
    row = serializers.CharField(source="seat.row_label", read_only=True)
    number = serializers.IntegerField(source="seat.seat_number", read_only=True)
    label = serializers.CharField(source="seat.label", read_only=True)
    category = serializers.CharField(source="seat.category.category", read_only=True)
    price = serializers.DecimalField(
        source="seat.category.price", max_digits=8, decimal_places=2, read_only=True
    )
    # Never expose who locked it — that leaks user info
    status = serializers.SerializerMethodField()
    is_mine = serializers.SerializerMethodField()

    class Meta:
        model = ShowSeat
        fields = ["id", "seat_id", "row", "number", "label", "category", "price", "status", "is_mine"]

    def get_status(self, obj: ShowSeat) -> str:
        """Return effective status — treat expired locks as AVAILABLE."""
        if obj.is_lock_expired:
            return ShowSeat.StatusChoices.AVAILABLE
        return obj.status

    def get_is_mine(self, obj: ShowSeat) -> bool:
        """True if this seat is locked by the requesting user."""
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return (
                obj.status == ShowSeat.StatusChoices.LOCKED
                and obj.locked_by_id == request.user.pk
                and not obj.is_lock_expired
            )
        return False
