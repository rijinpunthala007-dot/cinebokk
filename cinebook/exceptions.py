"""
CineBook — Custom DRF Exception Handler
=========================================
Returns a consistent JSON error shape for ALL exceptions:
  {
    "error": true,
    "code": "<machine-readable code>",
    "message": "<human-readable message>",
    "details": {...}   (optional, for validation errors)
  }

Never exposes stack traces or Django internals to the client.
"""

import logging
from typing import Any

from django.core.exceptions import PermissionDenied, ValidationError as DjangoValidationError
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import (
    APIException,
    AuthenticationFailed,
    NotAuthenticated,
    PermissionDenied as DRFPermissionDenied,
    ValidationError,
)
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_default_handler

logger = logging.getLogger("cinebook.exceptions")


class SeatUnavailableError(APIException):
    """Raised when a seat is already locked/booked by another user."""

    status_code = status.HTTP_409_CONFLICT
    default_code = "seat_unavailable"
    default_detail = "One or more seats are no longer available."


class PaymentError(APIException):
    """Raised when the simulated payment gateway rejects the transaction."""

    status_code = status.HTTP_402_PAYMENT_REQUIRED
    default_code = "payment_failed"
    default_detail = "Payment could not be processed. Please try again."


class BookingExpiredError(APIException):
    """Raised when the seat lock has expired before payment confirmation."""

    status_code = status.HTTP_410_GONE
    default_code = "booking_expired"
    default_detail = "Your seat reservation has expired. Please select seats again."


class ShowNotAvailableError(APIException):
    """Raised when a show is in the past or otherwise unavailable."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "show_not_available"
    default_detail = "This show is no longer available for booking."


def cinebook_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    """
    Custom DRF exception handler that normalises all errors into a consistent
    JSON shape and prevents internal details from leaking to the client.

    Args:
        exc: The exception raised by the view.
        context: DRF context dict containing request, view, etc.

    Returns:
        A Response with a normalised error payload, or None if the exception
        is not recognised (Django will then return a 500).
    """
    # Let DRF process standard API exceptions first
    response = drf_default_handler(exc, context)

    # Map Django exceptions to DRF equivalents
    if response is None:
        if isinstance(exc, Http404):
            exc = APIException(detail="The requested resource was not found.")
            exc.status_code = status.HTTP_404_NOT_FOUND
            exc.default_code = "not_found"
            response = Response(status=status.HTTP_404_NOT_FOUND)
        elif isinstance(exc, (PermissionDenied, DjangoValidationError)):
            exc = APIException(detail=str(exc))
            exc.status_code = status.HTTP_400_BAD_REQUEST
            exc.default_code = "bad_request"
            response = Response(status=status.HTTP_400_BAD_REQUEST)
        else:
            # Unknown exception — log it server-side, return generic 500
            logger.exception(
                "Unhandled exception in view %s: %s",
                context.get("view", "unknown"),
                exc,
            )
            return Response(
                {
                    "error": True,
                    "code": "internal_server_error",
                    "message": "An unexpected error occurred. Please try again later.",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # Log 5xx errors server-side
    if response.status_code >= 500:
        logger.error(
            "5xx error in view %s: %s — %s",
            context.get("view", "unknown"),
            exc.__class__.__name__,
            exc,
        )

    # Normalise the response body
    payload = _build_error_payload(exc, response)
    response.data = payload
    return response


def _build_error_payload(exc: Exception, response: Response) -> dict[str, Any]:
    """
    Build a normalised error payload from the exception and DRF response.

    Args:
        exc: The original exception.
        response: The DRF response (may have .data from default handler).

    Returns:
        A dict with error, code, message, and optional details keys.
    """
    code = getattr(exc, "default_code", "error")
    detail = getattr(exc, "detail", str(exc))

    if isinstance(detail, list):
        # Single field validation error list
        message = "; ".join(str(d) for d in detail)
        details = None
    elif isinstance(detail, dict):
        # Multi-field validation errors — surface them in 'details'
        message = "Validation failed. Check the 'details' field for specific errors."
        details = {
            field: [str(e) for e in errors] if isinstance(errors, list) else [str(errors)]
            for field, errors in detail.items()
        }
    else:
        message = str(detail)
        details = None

    payload: dict[str, Any] = {
        "error": True,
        "code": code,
        "message": message,
    }
    if details:
        payload["details"] = details

    return payload
