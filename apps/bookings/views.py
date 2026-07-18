"""
CineBook — Bookings API Views
==============================
All endpoints are authenticated (IsAuthenticated).
Seat locking and booking confirmation delegate entirely to the service layer.
"""

import logging
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.bookings.models import Booking
from apps.bookings.serializers import (
    BookingSerializer,
    CancelBookingRequestSerializer,
    ConfirmBookingRequestSerializer,
    LockSeatsRequestSerializer,
)
from apps.bookings.services import cancel_booking, confirm_booking, lock_seats
from cinebook.exceptions import (
    BookingExpiredError,
    PaymentError,
    SeatUnavailableError,
    ShowNotAvailableError,
)

logger = logging.getLogger("apps.bookings")


class LockSeatsView(APIView):
    """
    POST /api/v1/bookings/lock-seats/
    Attempt to lock the requested seats for 5 minutes.
    Returns lock expiry timestamp for the frontend countdown timer.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request) -> Response:
        serializer = LockSeatsRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": True, "code": "validation_error", "message": "Invalid request.",
                 "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = lock_seats(
                user=request.user,
                show_id=serializer.validated_data["show_id"],
                seat_ids=serializer.validated_data["seat_ids"],
            )
        except (ShowNotAvailableError, SeatUnavailableError) as exc:
            return Response(
                {"error": True, "code": exc.default_code, "message": str(exc.detail)},
                status=exc.status_code,
            )
        except ValueError as exc:
            return Response(
                {"error": True, "code": "invalid_request", "message": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "message": f"{len(result.locked_show_seats)} seat(s) locked successfully.",
                "lock_expiry": result.lock_expiry.isoformat(),
                "locked_seats": [ss.seat.label for ss in result.locked_show_seats],
            },
            status=status.HTTP_200_OK,
        )


class ConfirmBookingView(APIView):
    """
    POST /api/v1/bookings/confirm/
    Confirm a booking after payment. Returns booking details on success.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request) -> Response:
        serializer = ConfirmBookingRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": True, "code": "validation_error", "message": "Invalid request.",
                 "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            booking = confirm_booking(
                user=request.user,
                show_id=serializer.validated_data["show_id"],
                seat_ids=serializer.validated_data["seat_ids"],
                payment_data=serializer.validated_data["payment"],
            )
        except (ShowNotAvailableError, SeatUnavailableError, BookingExpiredError, PaymentError) as exc:
            return Response(
                {"error": True, "code": exc.default_code, "message": str(exc.detail)},
                status=exc.status_code,
            )
        except ValueError as exc:
            return Response(
                {"error": True, "code": "invalid_request", "message": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        booking_data = BookingSerializer(booking).data
        return Response(
            {"message": "Booking confirmed!", "booking": booking_data},
            status=status.HTTP_201_CREATED,
        )


class MyBookingsView(APIView):
    """GET /api/v1/bookings/my-bookings/ — Paginated booking history for the current user."""

    permission_classes = [IsAuthenticated]

    def get(self, request) -> Response:
        bookings = (
            Booking.objects
            .filter(customer=request.user)
            .select_related("show__movie", "show__screen__theater")
            .prefetch_related("booking_seats__seat__category")
            .order_by("-created_at")
        )

        # Manual pagination (simple, no need for DRF pagination overhead here)
        page = max(1, int(request.query_params.get("page", 1)))
        page_size = 10
        total = bookings.count()
        bookings_page = bookings[(page - 1) * page_size: page * page_size]

        serializer = BookingSerializer(bookings_page, many=True)
        return Response({
            "count": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
            "results": serializer.data,
        })


class BookingDetailView(APIView):
    """GET /api/v1/bookings/my-bookings/{booking_ref}/ — Single booking detail."""

    permission_classes = [IsAuthenticated]

    def get(self, request, booking_ref) -> Response:
        try:
            booking = (
                Booking.objects
                .select_related("show__movie", "show__screen__theater")
                .prefetch_related("booking_seats__seat__category")
                .get(booking_ref=booking_ref, customer=request.user)
            )
        except Booking.DoesNotExist:
            return Response(
                {"error": True, "code": "not_found", "message": "Booking not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = BookingSerializer(booking)
        return Response(serializer.data)


class CancelBookingView(APIView):
    """POST /api/v1/bookings/cancel/{booking_ref}/ — Cancel a booking."""

    permission_classes = [IsAuthenticated]

    def post(self, request, booking_ref) -> Response:
        serializer = CancelBookingRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": True, "code": "validation_error", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            booking = cancel_booking(
                user=request.user,
                booking_ref=booking_ref,
                reason=serializer.validated_data.get("reason", ""),
            )
        except ValueError as exc:
            return Response(
                {"error": True, "code": "cancellation_error", "message": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {"message": "Booking cancelled successfully.", "status": booking.status},
            status=status.HTTP_200_OK,
        )
