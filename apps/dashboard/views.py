"""
CineBook — Dashboard API Views
================================
Staff-only aggregation views for the admin dashboard.
"""

import logging
from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, Sum, Q
from django.utils import timezone
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.bookings.models import Booking
from apps.shows.models import Show, ShowSeat

logger = logging.getLogger("apps.dashboard")


class DashboardSummaryView(APIView):
    """
    GET /api/v1/dashboard/summary/
    Today's key metrics: revenue, bookings, occupancy.
    Staff only.
    """

    permission_classes = [IsAdminUser]

    def get(self, request) -> Response:
        today = timezone.now().date()

        # Today's confirmed bookings
        today_bookings = Booking.objects.filter(
            status=Booking.StatusChoices.CONFIRMED,
            booked_at__date=today,
        )

        total_revenue = today_bookings.aggregate(
            total=Sum("total_amount")
        )["total"] or Decimal("0.00")

        bookings_count = today_bookings.count()

        # Occupancy: booked / total show seats for today's active shows
        today_shows = Show.objects.filter(date=today, is_active=True)
        total_seats = ShowSeat.objects.filter(show__in=today_shows).count()
        booked_seats = ShowSeat.objects.filter(
            show__in=today_shows,
            status=ShowSeat.StatusChoices.BOOKED,
        ).count()

        occupancy_pct = (booked_seats / total_seats * 100) if total_seats > 0 else 0

        # Week-over-week comparison
        week_ago = today - timedelta(days=7)
        last_week_revenue = Booking.objects.filter(
            status=Booking.StatusChoices.CONFIRMED,
            booked_at__date=week_ago,
        ).aggregate(total=Sum("total_amount"))["total"] or Decimal("0.00")

        return Response({
            "today": str(today),
            "revenue": {
                "today": float(total_revenue),
                "last_week_same_day": float(last_week_revenue),
            },
            "bookings": {
                "today": bookings_count,
            },
            "occupancy": {
                "percentage": round(occupancy_pct, 1),
                "booked_seats": booked_seats,
                "total_seats": total_seats,
            },
            "shows_today": today_shows.count(),
        })


class TodayShowsView(APIView):
    """
    GET /api/v1/dashboard/shows/
    Today's shows with seat fill rates.
    """

    permission_classes = [IsAdminUser]

    def get(self, request) -> Response:
        today = timezone.now().date()
        shows = (
            Show.objects
            .filter(date=today, is_active=True)
            .select_related("movie", "screen__theater")
            .annotate(
                total_show_seats=Count("show_seats"),
                booked_show_seats=Count(
                    "show_seats",
                    filter=Q(show_seats__status=ShowSeat.StatusChoices.BOOKED),
                ),
            )
            .order_by("start_time")
        )

        data = []
        for show in shows:
            total = show.total_show_seats
            booked = show.booked_show_seats
            pct = (booked / total * 100) if total > 0 else 0
            data.append({
                "id": show.pk,
                "movie": show.movie.title,
                "theater": show.screen.theater.name,
                "screen": show.screen.name,
                "start_time": show.start_time,
                "language": show.language,
                "occupancy_pct": round(pct, 1),
                "booked": booked,
                "total": total,
            })

        return Response({"shows": data, "count": len(data)})


class RevenueView(APIView):
    """
    GET /api/v1/dashboard/revenue/
    Revenue breakdown for the last 30 days.
    """

    permission_classes = [IsAdminUser]

    def get(self, request) -> Response:
        from django.db.models.functions import TruncDate

        thirty_days_ago = timezone.now() - timedelta(days=30)

        daily_revenue = (
            Booking.objects
            .filter(
                status=Booking.StatusChoices.CONFIRMED,
                booked_at__gte=thirty_days_ago,
            )
            .annotate(date=TruncDate("booked_at"))
            .values("date")
            .annotate(revenue=Sum("total_amount"), count=Count("id"))
            .order_by("date")
        )

        total = sum(float(d["revenue"]) for d in daily_revenue)

        return Response({
            "period": "last_30_days",
            "total_revenue": total,
            "daily": [
                {
                    "date": str(d["date"]),
                    "revenue": float(d["revenue"]),
                    "bookings": d["count"],
                }
                for d in daily_revenue
            ],
        })
