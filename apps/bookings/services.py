"""
CineBook — Booking Service
============================
The single source of truth for all seat locking and booking logic.

CRITICAL CONCURRENCY NOTES:
- All seat status mutations use select_for_update() + transaction.atomic().
- select_for_update() acquires a row-level write lock at the DB level,
  which means two concurrent requests for the same seat will serialize —
  the second will block until the first commits or rolls back.
- We never trust the frontend for seat availability — every lock/confirm
  re-validates server-side inside the same atomic transaction.
- Expired locks are treated as AVAILABLE inline, without a separate query.

All public functions in this module are the ONLY place that mutates
ShowSeat.status. Views must not change ShowSeat.status directly.
"""

import logging
import uuid
from datetime import timedelta
from decimal import Decimal
from typing import NamedTuple

from django.conf import settings
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone

from apps.bookings.models import Booking, BookingSeat
from apps.shows.models import Show, ShowSeat
from cinebook.exceptions import (
    BookingExpiredError,
    PaymentError,
    SeatUnavailableError,
    ShowNotAvailableError,
)

logger = logging.getLogger("apps.bookings.services")

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

class LockResult(NamedTuple):
    """Result returned by lock_seats()."""
    locked_show_seats: list[ShowSeat]
    lock_expiry: object   # datetime


class PaymentResult(NamedTuple):
    """Result returned by mock_payment_gateway()."""
    success: bool
    payment_ref: str
    failure_reason: str


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

@transaction.atomic
def lock_seats(
    user: User,
    show_id: int,
    seat_ids: list[int],
) -> LockResult:
    """
    Atomically lock a set of seats for a given show for the requesting user.

    Uses select_for_update() to prevent concurrent booking of the same seat.
    Inline-expires any stale locks (locked_at older than SEAT_LOCK_MINUTES)
    before checking availability, so a timed-out hold doesn't block new users.

    Args:
        user: The authenticated user requesting the lock.
        show_id: ID of the Show to lock seats for.
        seat_ids: List of Seat PKs the user wants to book.

    Returns:
        LockResult with the locked ShowSeat objects and expiry datetime.

    Raises:
        ShowNotAvailableError: If the show doesn't exist, is inactive, or is in the past.
        ValueError: If seat_ids is empty or contains duplicates.
        SeatUnavailableError: If any of the requested seats are already locked/booked.
    """
    if not seat_ids:
        raise ValueError("At least one seat must be selected.")
    if len(seat_ids) != len(set(seat_ids)):
        raise ValueError("Duplicate seat IDs are not allowed.")
    if len(seat_ids) > 10:
        raise ValueError("Cannot book more than 10 seats at once.")

    # --- Validate the show ---
    try:
        show = Show.objects.select_related("movie", "screen").get(pk=show_id)
    except Show.DoesNotExist:
        raise ShowNotAvailableError("Show not found.")

    if not show.is_active:
        raise ShowNotAvailableError("This show is no longer active.")

    if show.start_time <= timezone.now():
        raise ShowNotAvailableError(
            "This show has already started. Please select a future show."
        )

    # --- Lock all requested ShowSeat rows with select_for_update() ---
    # ORDER BY is required to prevent deadlocks when two transactions lock
    # overlapping but differently-ordered seat sets.
    show_seats = (
        ShowSeat.objects
        .select_for_update()
        .filter(show_id=show_id, seat_id__in=seat_ids)
        .select_related("seat__category")
        .order_by("seat_id")
    )

    # Validate we got all requested seats
    found_seat_ids = {ss.seat_id for ss in show_seats}
    missing = set(seat_ids) - found_seat_ids
    if missing:
        raise SeatUnavailableError(
            f"Seat(s) not found for this show: {missing}. "
            "The seat map may be outdated — please refresh."
        )

    # --- Inline expiry: treat stale LOCKED rows as AVAILABLE ---
    lock_minutes = getattr(settings, "SEAT_LOCK_MINUTES", 5)
    expiry_threshold = timezone.now() - timedelta(minutes=lock_minutes)
    expired_ids = []
    for ss in show_seats:
        if (
            ss.status == ShowSeat.StatusChoices.LOCKED
            and ss.locked_at is not None
            and ss.locked_at < expiry_threshold
        ):
            expired_ids.append(ss.pk)

    if expired_ids:
        ShowSeat.objects.filter(pk__in=expired_ids).update(
            status=ShowSeat.StatusChoices.AVAILABLE,
            locked_by=None,
            locked_at=None,
        )
        # Refresh the queryset after expiry fix
        show_seats = list(
            ShowSeat.objects
            .select_for_update()
            .filter(show_id=show_id, seat_id__in=seat_ids)
            .select_related("seat__category")
            .order_by("seat_id")
        )

    # --- Check availability ---
    unavailable = []
    for ss in show_seats:
        if ss.status == ShowSeat.StatusChoices.BOOKED:
            unavailable.append(ss.seat.label)
        elif ss.status == ShowSeat.StatusChoices.LOCKED and ss.locked_by_id != user.pk:
            # Another user holds the lock
            unavailable.append(ss.seat.label)

    if unavailable:
        seat_list = ", ".join(unavailable)
        raise SeatUnavailableError(
            f"Seat(s) {seat_list} are no longer available. "
            "Please reselect from the updated seat map."
        )

    # --- Apply the lock ---
    now = timezone.now()
    lock_expiry = now + timedelta(minutes=lock_minutes)

    ShowSeat.objects.filter(
        pk__in=[ss.pk for ss in show_seats]
    ).update(
        status=ShowSeat.StatusChoices.LOCKED,
        locked_by=user,
        locked_at=now,
    )

    # Reload to return fresh state
    locked_seats = list(
        ShowSeat.objects
        .filter(pk__in=[ss.pk for ss in show_seats])
        .select_related("seat__category")
    )

    logger.info(
        "User %s locked %d seat(s) for show %d. Expiry: %s",
        user.username, len(locked_seats), show_id, lock_expiry.isoformat(),
    )


    return LockResult(locked_show_seats=locked_seats, lock_expiry=lock_expiry)


def confirm_booking(
    user: User,
    show_id: int,
    seat_ids: list[int],
    payment_data: dict,
) -> Booking:

    """
    Confirm a booking after successful (simulated) payment.

    This is the most critical transactional unit in CineBook.
    It re-validates seat locks server-side (never trusting client),
    processes the mock payment, and atomically creates Booking + BookingSeat
    records while flipping ShowSeat.status to BOOKED.

    TRANSACTION DESIGN:
    - We do NOT use a single @transaction.atomic wrapper here.
    - Reason: If payment fails and we raise PaymentError inside an atomic block,
      the entire transaction rolls back — INCLUDING the lock-release UPDATE.
      That would leave seats permanently locked until the cron sweeper fires.
    - Instead, we use three separate atomic blocks:
      1. Validation: reads seat status under select_for_update (releases lock after read)
      2. On payment failure: release locks in its own committed transaction
      3. On payment success: create Booking + BookingSeat + update ShowSeat atomically

    Args:
        user: The authenticated user confirming the booking.
        show_id: ID of the Show being booked.
        seat_ids: List of Seat PKs the user wants to confirm.
        payment_data: Dict with card/payment info (mock — not processed).

    Returns:
        A confirmed Booking instance.

    Raises:
        ShowNotAvailableError: If the show no longer exists or is in the past.
        BookingExpiredError: If the seat lock has expired.
        SeatUnavailableError: If a seat was taken by another user.
        PaymentError: If the mock payment gateway rejects the transaction.
    """
    if not seat_ids:
        raise ValueError("No seats provided for booking confirmation.")

    # --- Re-validate the show (no transaction needed for reads) ---
    try:
        show = Show.objects.select_related("movie", "screen").get(pk=show_id)
    except Show.DoesNotExist:
        raise ShowNotAvailableError("Show not found.")

    if show.start_time <= timezone.now():
        raise ShowNotAvailableError("This show has already started.")

    # --- Phase 1: Validate seat locks in an atomic block with select_for_update ---
    # The transaction is released after validation so subsequent phases
    # use their own transactions.
    lock_minutes = getattr(settings, "SEAT_LOCK_MINUTES", 5)
    expiry_threshold = timezone.now() - timedelta(minutes=lock_minutes)
    expired = []
    unavailable = []
    total_amount = Decimal("0.00")
    seat_pks_to_process: list[int] = []

    with transaction.atomic():
        show_seats = list(
            ShowSeat.objects
            .select_for_update()
            .filter(show_id=show_id, seat_id__in=seat_ids)
            .select_related("seat__category")
            .order_by("seat_id")
        )

        if len(show_seats) != len(seat_ids):
            raise SeatUnavailableError(
                "One or more seats no longer exist for this show. Please refresh."
            )

        for ss in show_seats:
            seat_pks_to_process.append(ss.pk)
            if ss.status == ShowSeat.StatusChoices.BOOKED:
                unavailable.append(ss.seat.label)
            elif ss.status == ShowSeat.StatusChoices.LOCKED and ss.locked_by_id != user.pk:
                unavailable.append(ss.seat.label)
            elif ss.status == ShowSeat.StatusChoices.LOCKED and ss.locked_by_id == user.pk:
                if ss.locked_at and ss.locked_at < expiry_threshold:
                    expired.append(ss.seat.label)
                else:
                    total_amount += ss.seat.category.price
            elif ss.status == ShowSeat.StatusChoices.AVAILABLE:
                # Seat is no longer locked by us — treat as unavailable
                unavailable.append(ss.seat.label)
        # select_for_update released when this atomic block exits

    if expired:
        seat_list = ", ".join(expired)
        raise BookingExpiredError(
            f"Your reservation for seat(s) {seat_list} has expired. "
            "Please select seats again."
        )

    if unavailable:
        seat_list = ", ".join(unavailable)
        raise SeatUnavailableError(
            f"Seat(s) {seat_list} are no longer available. "
            "Please reselect from the updated seat map."
        )

    # --- Phase 2: Process mock payment (outside any transaction) ---
    payment_result = mock_payment_gateway(payment_data, total_amount)

    if not payment_result.success:
        # Phase 2a: Payment failed — release locks in a COMMITTED transaction.
        # This is a separate atomic block so the release is persisted even though
        # we're about to raise an exception (which does NOT roll back this block).
        with transaction.atomic():
            ShowSeat.objects.filter(pk__in=seat_pks_to_process).update(
                status=ShowSeat.StatusChoices.AVAILABLE,
                locked_by=None,
                locked_at=None,
            )

        logger.warning(
            "Payment failed for user %s, show %d: %s",
            user.username, show_id, payment_result.failure_reason,
        )
        raise PaymentError(
            f"Payment declined: {payment_result.failure_reason}. "
            "Please check your payment details and try again."
        )

    # --- Phase 3: Payment succeeded — create Booking + BookingSeat atomically ---
    with transaction.atomic():
        # Re-fetch show_seats inside this atomic block for the create operations
        show_seats_for_create = list(
            ShowSeat.objects
            .select_for_update()
            .filter(pk__in=seat_pks_to_process)
            .select_related("seat__category")
            .order_by("pk")
        )

        now = timezone.now()
        booking = Booking.objects.create(
            customer=user,
            show=show,
            status=Booking.StatusChoices.CONFIRMED,
            total_amount=total_amount,
            payment_ref=payment_result.payment_ref,
            booked_at=now,
        )

        booking_seat_records = [
            BookingSeat(
                booking=booking,
                show_seat=ss,
                seat=ss.seat,
                price_at_booking=ss.seat.category.price,
            )
            for ss in show_seats_for_create
        ]
        BookingSeat.objects.bulk_create(booking_seat_records)

        ShowSeat.objects.filter(pk__in=seat_pks_to_process).update(
            status=ShowSeat.StatusChoices.BOOKED,
            locked_by=None,
            locked_at=None,
        )

    logger.info(
        "Booking confirmed: ref=%s, user=%s, show=%d, seats=%d, total=₹%s",
        str(booking.booking_ref)[:8].upper(),
        user.username,
        show_id,
        len(seat_pks_to_process),
        total_amount,
    )

    return booking


    return booking


@transaction.atomic
def cancel_booking(user: User, booking_ref: uuid.UUID, reason: str = "") -> Booking:
    """
    Cancel a confirmed booking and release the associated seats.

    Policy:
    - Only CONFIRMED bookings can be cancelled.
    - Cancellation is allowed up to 1 hour before the show starts.
    - Staff can cancel any booking at any time.

    Args:
        user: The authenticated user requesting cancellation.
        booking_ref: Public UUID reference of the booking to cancel.
        reason: Optional reason for cancellation.

    Returns:
        The updated Booking instance.

    Raises:
        ValueError: If the booking cannot be cancelled due to policy or state.
    """
    try:
        booking = (
            Booking.objects
            .select_for_update()
            .select_related("show__movie", "customer")
            .prefetch_related("booking_seats__show_seat")
            .get(booking_ref=booking_ref)
        )
    except Booking.DoesNotExist:
        raise ValueError("Booking not found.")

    # Authorisation check — only owner or staff can cancel
    if booking.customer_id != user.pk and not user.is_staff:
        raise ValueError("You do not have permission to cancel this booking.")

    if booking.status != Booking.StatusChoices.CONFIRMED:
        raise ValueError(
            f"Only CONFIRMED bookings can be cancelled. "
            f"Current status: {booking.status}."
        )

    # Policy: 1-hour cancellation window (bypass for staff)
    if not user.is_staff:
        cancellation_deadline = booking.show.start_time - timedelta(hours=1)
        if timezone.now() >= cancellation_deadline:
            raise ValueError(
                "Cancellations must be made at least 1 hour before the show starts."
            )

    # Release seats (BOOKED → AVAILABLE)
    show_seat_pks = [bs.show_seat_id for bs in booking.booking_seats.all()]
    ShowSeat.objects.filter(pk__in=show_seat_pks).update(
        status=ShowSeat.StatusChoices.AVAILABLE,
        locked_by=None,
        locked_at=None,
    )

    booking.status = Booking.StatusChoices.CANCELLED
    booking.cancellation_reason = reason or "Cancelled by customer"
    booking.save(update_fields=["status", "cancellation_reason", "updated_at"])

    logger.info(
        "Booking cancelled: ref=%s, user=%s, reason=%s",
        str(booking.booking_ref)[:8].upper(), user.username, reason,
    )

    return booking


# ---------------------------------------------------------------------------
# Mock Payment Gateway
# ---------------------------------------------------------------------------

def mock_payment_gateway(payment_data: dict, amount: Decimal) -> PaymentResult:
    """
    Simulated payment gateway — always succeeds in development.

    In a real system, this would call Razorpay/Stripe/Braintree.
    For testing payment failures, set payment_data["__force_fail"] = True.

    Args:
        payment_data: Dict with card_number, expiry, cvv, name_on_card.
        amount: Total amount to charge in INR.

    Returns:
        PaymentResult with success flag and payment reference.
    """
    # Allow tests to force a failure
    if payment_data.get("__force_fail"):
        return PaymentResult(
            success=False,
            payment_ref="",
            failure_reason="Simulated payment failure (forced by test)",
        )

    # Basic validation — in production this would be done by the gateway
    card_number = str(payment_data.get("card_number", "")).replace(" ", "")
    if not card_number or len(card_number) < 13:
        return PaymentResult(
            success=False,
            payment_ref="",
            failure_reason="Invalid card number.",
        )

    expiry = payment_data.get("expiry", "").strip()
    if not expiry or len(expiry) < 4:
        return PaymentResult(
            success=False,
            payment_ref="",
            failure_reason="Invalid expiry date.",
        )

    cvv = str(payment_data.get("cvv", "")).strip()
    if not cvv or len(cvv) < 3:
        return PaymentResult(
            success=False,
            payment_ref="",
            failure_reason="Invalid CVV.",
        )

    # Generate a mock payment reference
    payment_ref = f"MOCK-{uuid.uuid4().hex[:12].upper()}"

    logger.info(
        "Mock payment processed: ref=%s, amount=₹%s",
        payment_ref, amount,
    )

    return PaymentResult(success=True, payment_ref=payment_ref, failure_reason="")
