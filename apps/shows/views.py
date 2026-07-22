"""
CineBook — Shows API Views
===========================
"""

import logging
from datetime import date, timedelta

from django.conf import settings
from django.utils import timezone
from django.utils.crypto import constant_time_compare
from rest_framework import status
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.movies.views import MoviesReadThrottle
from apps.shows.models import Show, ShowSeat
from apps.shows.services import refresh_showtimes
from .serializers import ShowDetailSerializer, ShowListSerializer, ShowSeatSerializer

logger = logging.getLogger("apps.shows")


class ShowListView(ListAPIView):
    """
    GET /api/v1/shows/
    List shows with filtering by movie, date, city, and language.
    Only shows in the next 7 days from today are listed by default.

    Query params:
    - movie: Movie ID
    - date: YYYY-MM-DD (defaults to today)
    - city: Filter by theater city
    - language: Filter by show language
    """

    serializer_class = ShowListSerializer
    permission_classes = [AllowAny]
    throttle_classes = [MoviesReadThrottle]

    def get_queryset(self):
        qs = (
            Show.objects
            .filter(is_active=True, start_time__gt=timezone.now())
            .select_related("movie", "screen__theater")
            .prefetch_related("show_seats")
        )

        movie_id = self.request.query_params.get("movie", "").strip()
        if movie_id:
            try:
                qs = qs.filter(movie_id=int(movie_id))
            except (ValueError, TypeError):
                pass

        # Date filter — default to today, max 7 days ahead
        date_str = self.request.query_params.get("date", "").strip()
        if date_str:
            try:
                show_date = date.fromisoformat(date_str)
                qs = qs.filter(date=show_date)
            except ValueError:
                pass
        else:
            qs = qs.filter(date__gte=timezone.now().date())

        city = self.request.query_params.get("city", "").strip()
        if city:
            qs = qs.filter(screen__theater__city__name__iexact=city)

        language = self.request.query_params.get("language", "").strip()
        if language:
            qs = qs.filter(language__iexact=language)

        return qs.order_by("date", "start_time")


class ShowDetailView(RetrieveAPIView):
    """GET /api/v1/shows/{id}/ — Show detail including screen and movie info."""

    serializer_class = ShowDetailSerializer
    permission_classes = [AllowAny]
    throttle_classes = [MoviesReadThrottle]
    queryset = Show.objects.filter(is_active=True).select_related("movie", "screen__theater")


class ShowSeatMapView(APIView):
    """
    GET /api/v1/shows/{pk}/seat-map/
    Returns the full seat grid for a show, grouped by row and category.
    Seat statuses are refreshed on every call (expired locks shown as AVAILABLE).
    """

    permission_classes = [AllowAny]
    throttle_classes = [MoviesReadThrottle]

    def get(self, request, pk: int) -> Response:
        try:
            show = Show.objects.select_related("screen").get(pk=pk, is_active=True)
        except Show.DoesNotExist:
            return Response(
                {"error": True, "code": "not_found", "message": "Show not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        show_seats = (
            ShowSeat.objects
            .filter(show=show)
            .select_related("seat__category")
            .order_by("seat__row_label", "seat__seat_number")
        )

        # Inline: release expired locks before building the map
        from apps.shows.cron import release_expired_locks
        release_expired_locks()

        # Reload after expiry sweep
        show_seats = (
            ShowSeat.objects
            .filter(show=show)
            .select_related("seat__category")
            .order_by("seat__row_label", "seat__seat_number")
        )

        serializer = ShowSeatSerializer(
            show_seats, many=True, context={"request": request}
        )

        # Group by row for the frontend seat map grid
        rows: dict[str, list] = {}
        for seat_data in serializer.data:
            row = seat_data["row"]
            if row not in rows:
                rows[row] = []
            rows[row].append(seat_data)

        # Build category pricing summary
        categories = {}
        for ss in show_seats:
            cat = ss.seat.category.category
            if cat not in categories:
                categories[cat] = float(ss.seat.category.price)

        return Response({
            "show_id": show.pk,
            "movie_title": show.movie.title,
            "start_time": show.start_time,
            "screen_name": show.screen.name,
            "categories": categories,
            "rows": rows,
            "total_seats": show_seats.count(),
            "available_seats": show_seats.filter(status=ShowSeat.StatusChoices.AVAILABLE).count(),
        })


class RefreshShowtimesView(APIView):
    """
    POST /api/v1/internal/refresh-showtimes/
    Meant to be pinged daily by an external free cron service (e.g.
    cron-job.org) so currently-released movies' shows stay in the current
    [today, today+6] window without a manual redeploy — see
    apps.shows.services.refresh_showtimes.

    Auth: shared secret via either
    - header  X-Cron-Secret: <CRON_SECRET>
    - query param  ?token=<CRON_SECRET>
    Rejects with 403 if CRON_SECRET is unset server-side, or the caller's
    value is missing/incorrect.
    """

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = []

    def post(self, request) -> Response:
        expected = getattr(settings, "CRON_SECRET", "")
        provided = request.headers.get("X-Cron-Secret") or request.query_params.get("token", "")

        if not expected or not provided or not constant_time_compare(provided, expected):
            logger.warning("Rejected refresh-showtimes request: bad or missing CRON_SECRET.")
            return Response(
                {"status": "forbidden"},
                status=status.HTTP_403_FORBIDDEN,
            )

        updated = refresh_showtimes()
        return Response({"status": "ok", "shows_updated": updated})
