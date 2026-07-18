"""
CineBook — Seat Locking Unit Tests
====================================
Tests for the highest-risk code path: concurrency-safe seat booking.

Coverage:
1. Successful seat lock
2. Expired lock treated as AVAILABLE on next lock attempt
3. Seat locked by another user raises SeatUnavailableError
4. Already-BOOKED seat raises SeatUnavailableError
5. Empty seat_ids raises ValueError
6. Duplicate seat_ids raises ValueError
7. Exceeding seat limit raises ValueError
8. Confirm booking — full happy path
9. Confirm booking — expired lock raises BookingExpiredError
10. Confirm booking — seat taken raises SeatUnavailableError
11. Confirm booking — mock payment failure releases locks
12. Cancel booking — happy path
13. Cancel booking — past cancellation deadline raises ValueError
14. Cron sweeper releases expired locks

The concurrency race condition (two threads, same seat) is tested using
Django's TestCase with explicit lock manipulation rather than actual threads,
because SQLite doesn't support true concurrent select_for_update() in tests.
The service logic is correct for MySQL which does support row-level locking.
"""

import uuid
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from apps.bookings.models import Booking, BookingSeat
from apps.bookings.services import (
    cancel_booking,
    confirm_booking,
    lock_seats,
    mock_payment_gateway,
)
from apps.movies.models import Genre, Movie
from apps.shows.models import Show, ShowSeat
from apps.shows.cron import release_expired_locks
from apps.theaters.models import Seat, SeatCategory, Screen, Theater
from cinebook.exceptions import (
    BookingExpiredError,
    PaymentError,
    SeatUnavailableError,
    ShowNotAvailableError,
)


# ---------------------------------------------------------------------------
# Test Fixtures / Helpers
# ---------------------------------------------------------------------------

def make_user(username: str = "testuser", is_staff: bool = False) -> User:
    """Create a test user with a unique username."""
    return User.objects.create_user(
        username=username,
        email=f"{username}@cinebook.test",
        password="TestPass123!",
        is_staff=is_staff,
    )


def make_show_with_seats(
    num_seats: int = 5,
    start_offset_hours: int = 2,
) -> tuple[Show, list[Seat], list[ShowSeat]]:
    """
    Create a complete Show fixture with seats and ShowSeat records.

    Returns:
        Tuple of (show, [seat objects], [show_seat objects])
    """
    theater = Theater.objects.create(
        name="Test Cinema",
        city="Mumbai",
        address="123 Test Street",
    )
    screen = Screen.objects.create(
        theater=theater,
        name="Screen 1",
        total_capacity=num_seats,
    )
    genre, _ = Genre.objects.get_or_create(name="Action")
    movie = Movie.objects.create(
        title="Test Movie",
        description="Test",
        duration_minutes=120,
        language="English",
        release_date=timezone.now().date(),
        rating=Movie.RatingChoices.UA,
    )
    movie.genres.add(genre)

    seat_category = SeatCategory.objects.create(
        screen=screen,
        category=SeatCategory.CategoryChoices.CLASSIC,
        price=Decimal("200.00"),
    )

    seats = []
    for i in range(1, num_seats + 1):
        seat = Seat.objects.create(
            screen=screen,
            category=seat_category,
            row_label="A",
            seat_number=i,
        )
        seats.append(seat)

    start_time = timezone.now() + timedelta(hours=start_offset_hours)
    show = Show(
        movie=movie,
        screen=screen,
        start_time=start_time,
        language="English",
        is_active=True,
    )
    # Bypass save() auto-population for test control
    show.end_time = start_time + timedelta(minutes=120)
    show.date = start_time.date()
    show.save()

    show_seats = []
    for seat in seats:
        ss = ShowSeat.objects.create(
            show=show,
            seat=seat,
            status=ShowSeat.StatusChoices.AVAILABLE,
        )
        show_seats.append(ss)

    return show, seats, show_seats


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestLockSeats(TestCase):
    """Tests for the lock_seats() service function."""

    def setUp(self):
        self.user = make_user("alice")
        self.show, self.seats, self.show_seats = make_show_with_seats(5)

    def _seat_ids(self, indices: list[int]) -> list[int]:
        """Get seat PKs by index (0-based)."""
        return [self.seats[i].pk for i in indices]

    def test_successful_lock(self):
        """A user can lock available seats."""
        result = lock_seats(self.user, self.show.pk, self._seat_ids([0, 1]))
        self.assertEqual(len(result.locked_show_seats), 2)
        self.assertGreater(result.lock_expiry, timezone.now())

        # Verify DB state
        for ss in self.show_seats[:2]:
            ss.refresh_from_db()
            self.assertEqual(ss.status, ShowSeat.StatusChoices.LOCKED)
            self.assertEqual(ss.locked_by, self.user)
            self.assertIsNotNone(ss.locked_at)

    def test_expired_lock_treated_as_available(self):
        """An expired LOCKED seat is treated as AVAILABLE for a new user."""
        other_user = make_user("bob")

        # Manually set an expired lock on seat[0]
        ShowSeat.objects.filter(pk=self.show_seats[0].pk).update(
            status=ShowSeat.StatusChoices.LOCKED,
            locked_by=other_user,
            locked_at=timezone.now() - timedelta(minutes=10),  # 10 min ago = expired
        )

        # Alice should be able to lock it (expired lock should be released inline)
        result = lock_seats(self.user, self.show.pk, self._seat_ids([0]))
        self.assertEqual(len(result.locked_show_seats), 1)

        # Verify it's now locked by Alice
        self.show_seats[0].refresh_from_db()
        self.assertEqual(self.show_seats[0].locked_by, self.user)

    def test_seat_locked_by_other_user_raises_error(self):
        """Attempting to lock a seat held by another user raises SeatUnavailableError."""
        other_user = make_user("charlie")

        # Bob has a fresh (non-expired) lock on seat[0]
        ShowSeat.objects.filter(pk=self.show_seats[0].pk).update(
            status=ShowSeat.StatusChoices.LOCKED,
            locked_by=other_user,
            locked_at=timezone.now(),
        )

        with self.assertRaises(SeatUnavailableError):
            lock_seats(self.user, self.show.pk, self._seat_ids([0]))

    def test_booked_seat_raises_error(self):
        """Attempting to lock a BOOKED seat raises SeatUnavailableError."""
        ShowSeat.objects.filter(pk=self.show_seats[0].pk).update(
            status=ShowSeat.StatusChoices.BOOKED,
        )

        with self.assertRaises(SeatUnavailableError):
            lock_seats(self.user, self.show.pk, self._seat_ids([0]))

    def test_empty_seat_ids_raises_error(self):
        """lock_seats() with empty list raises ValueError."""
        with self.assertRaises(ValueError, msg="At least one seat must be selected."):
            lock_seats(self.user, self.show.pk, [])

    def test_duplicate_seat_ids_raises_error(self):
        """lock_seats() with duplicate seat IDs raises ValueError."""
        seat_id = self.seats[0].pk
        with self.assertRaises(ValueError):
            lock_seats(self.user, self.show.pk, [seat_id, seat_id])

    def test_too_many_seats_raises_error(self):
        """lock_seats() with more than 10 seats raises ValueError."""
        show, seats, _ = make_show_with_seats(num_seats=15)
        with self.assertRaises(ValueError):
            lock_seats(self.user, show.pk, [s.pk for s in seats[:11]])

    def test_past_show_raises_error(self):
        """Cannot lock seats for a show that has already started."""
        _, seats, _ = make_show_with_seats(start_offset_hours=-3)  # 3h ago
        show_id = Show.objects.latest("created_at").pk
        with self.assertRaises(ShowNotAvailableError):
            lock_seats(self.user, show_id, [seats[0].pk])

    def test_inactive_show_raises_error(self):
        """Cannot lock seats for an inactive show."""
        self.show.is_active = False
        self.show.save()
        with self.assertRaises(ShowNotAvailableError):
            lock_seats(self.user, self.show.pk, self._seat_ids([0]))

    def test_same_user_can_re_lock(self):
        """The same user can re-lock their already-locked seat (extends the hold)."""
        lock_seats(self.user, self.show.pk, self._seat_ids([0]))
        # Re-locking same seat should succeed
        result = lock_seats(self.user, self.show.pk, self._seat_ids([0]))
        self.assertEqual(len(result.locked_show_seats), 1)


class TestConfirmBooking(TestCase):
    """Tests for the confirm_booking() service function."""

    def setUp(self):
        self.user = make_user("diana")
        self.show, self.seats, self.show_seats = make_show_with_seats(3)
        self.valid_payment = {
            "card_number": "4111111111111111",
            "expiry": "12/27",
            "cvv": "123",
            "name_on_card": "Diana Test",
        }

    def _seat_ids(self, indices: list[int]) -> list[int]:
        return [self.seats[i].pk for i in indices]

    def _lock_seats_for_user(self, indices: list[int]) -> None:
        """Helper: manually apply lock for this user (avoids calling service in setup)."""
        ShowSeat.objects.filter(
            pk__in=[self.show_seats[i].pk for i in indices]
        ).update(
            status=ShowSeat.StatusChoices.LOCKED,
            locked_by=self.user,
            locked_at=timezone.now(),
        )

    def test_full_happy_path(self):
        """Full lock → confirm flow creates a CONFIRMED booking."""
        self._lock_seats_for_user([0, 1])
        booking = confirm_booking(
            self.user, self.show.pk, self._seat_ids([0, 1]), self.valid_payment
        )

        self.assertEqual(booking.status, Booking.StatusChoices.CONFIRMED)
        self.assertEqual(booking.customer, self.user)
        self.assertEqual(booking.booking_seats.count(), 2)
        self.assertEqual(booking.total_amount, Decimal("400.00"))  # 2 × 200
        self.assertIsNotNone(booking.payment_ref)
        self.assertTrue(booking.payment_ref.startswith("MOCK-"))

        # ShowSeats should now be BOOKED
        for ss in [self.show_seats[0], self.show_seats[1]]:
            ss.refresh_from_db()
            self.assertEqual(ss.status, ShowSeat.StatusChoices.BOOKED)
            self.assertIsNone(ss.locked_by)

    def test_expired_lock_raises_booking_expired_error(self):
        """Confirming a booking after the lock expired raises BookingExpiredError."""
        ShowSeat.objects.filter(
            pk__in=[self.show_seats[0].pk]
        ).update(
            status=ShowSeat.StatusChoices.LOCKED,
            locked_by=self.user,
            locked_at=timezone.now() - timedelta(minutes=10),  # Expired
        )

        with self.assertRaises(BookingExpiredError):
            confirm_booking(
                self.user, self.show.pk, self._seat_ids([0]), self.valid_payment
            )

    def test_seat_taken_by_another_user_raises_error(self):
        """Confirming when a seat has been taken by another user raises SeatUnavailableError."""
        other = make_user("eve")
        ShowSeat.objects.filter(pk=self.show_seats[0].pk).update(
            status=ShowSeat.StatusChoices.LOCKED,
            locked_by=other,
            locked_at=timezone.now(),
        )

        with self.assertRaises(SeatUnavailableError):
            confirm_booking(
                self.user, self.show.pk, self._seat_ids([0]), self.valid_payment
            )

    def test_payment_failure_releases_locks(self):
        """A payment failure releases the seat locks (no partial state)."""
        self._lock_seats_for_user([0, 1])
        bad_payment = {"__force_fail": True}

        with self.assertRaises(PaymentError):
            confirm_booking(self.user, self.show.pk, self._seat_ids([0, 1]), bad_payment)

        # Seats should be AVAILABLE again
        for ss in [self.show_seats[0], self.show_seats[1]]:
            ss.refresh_from_db()
            self.assertEqual(ss.status, ShowSeat.StatusChoices.AVAILABLE)

        # No booking should have been created
        self.assertEqual(Booking.objects.count(), 0)

    def test_no_seats_raises_error(self):
        """confirm_booking() with empty seat list raises ValueError."""
        with self.assertRaises(ValueError):
            confirm_booking(self.user, self.show.pk, [], self.valid_payment)


class TestCancelBooking(TestCase):
    """Tests for the cancel_booking() service function."""

    def setUp(self):
        self.user = make_user("frank")
        self.show, self.seats, self.show_seats = make_show_with_seats(2, start_offset_hours=3)
        self.staff = make_user("admin_staff", is_staff=True)

        # Create a confirmed booking manually
        self.booking = Booking.objects.create(
            customer=self.user,
            show=self.show,
            status=Booking.StatusChoices.CONFIRMED,
            total_amount=Decimal("400.00"),
            payment_ref="MOCK-TESTREF",
            booked_at=timezone.now(),
        )
        for ss in self.show_seats:
            ss.status = ShowSeat.StatusChoices.BOOKED
            ss.save()
            BookingSeat.objects.create(
                booking=self.booking,
                show_seat=ss,
                seat=ss.seat,
                price_at_booking=Decimal("200.00"),
            )

    def test_cancel_within_policy(self):
        """Cancellation within the 1-hour window succeeds."""
        updated = cancel_booking(self.user, self.booking.booking_ref, "Changed plans")
        self.assertEqual(updated.status, Booking.StatusChoices.CANCELLED)

        # Seats released
        for ss in self.show_seats:
            ss.refresh_from_db()
            self.assertEqual(ss.status, ShowSeat.StatusChoices.AVAILABLE)

    def test_cancel_past_deadline_raises_error(self):
        """Cancellation within 1 hour of show start is blocked."""
        # Move show to 30 min from now (within deadline)
        self.show.start_time = timezone.now() + timedelta(minutes=30)
        self.show.save()

        with self.assertRaises(ValueError, msg="Cancellations must be made at least 1 hour"):
            cancel_booking(self.user, self.booking.booking_ref)

    def test_staff_can_cancel_past_deadline(self):
        """Staff can cancel bookings even past the normal deadline."""
        self.show.start_time = timezone.now() + timedelta(minutes=10)
        self.show.save()

        updated = cancel_booking(self.staff, self.booking.booking_ref, "Admin override")
        self.assertEqual(updated.status, Booking.StatusChoices.CANCELLED)

    def test_other_user_cannot_cancel(self):
        """A different non-staff user cannot cancel someone else's booking."""
        intruder = make_user("intruder")
        with self.assertRaises(ValueError, msg="permission"):
            cancel_booking(intruder, self.booking.booking_ref)

    def test_cancel_already_cancelled_raises_error(self):
        """Cannot cancel an already-cancelled booking."""
        self.booking.status = Booking.StatusChoices.CANCELLED
        self.booking.save()
        with self.assertRaises(ValueError):
            cancel_booking(self.user, self.booking.booking_ref)


class TestMockPaymentGateway(TestCase):
    """Tests for the mock payment gateway."""

    def test_valid_payment_succeeds(self):
        result = mock_payment_gateway(
            {"card_number": "4111111111111111", "expiry": "12/27", "cvv": "123"},
            Decimal("400.00"),
        )
        self.assertTrue(result.success)
        self.assertTrue(result.payment_ref.startswith("MOCK-"))

    def test_forced_failure(self):
        result = mock_payment_gateway({"__force_fail": True}, Decimal("400.00"))
        self.assertFalse(result.success)
        self.assertEqual(result.payment_ref, "")

    def test_invalid_card_number(self):
        result = mock_payment_gateway(
            {"card_number": "123", "expiry": "12/27", "cvv": "123"},
            Decimal("400.00"),
        )
        self.assertFalse(result.success)

    def test_missing_cvv(self):
        result = mock_payment_gateway(
            {"card_number": "4111111111111111", "expiry": "12/27", "cvv": ""},
            Decimal("400.00"),
        )
        self.assertFalse(result.success)


class TestCronSweeper(TestCase):
    """Tests for the expired lock cron sweeper."""

    def test_sweeper_releases_expired_locks(self):
        """The sweeper correctly releases expired locks and returns count."""
        user = make_user("grace")
        _, _, show_seats = make_show_with_seats(3)

        # Set 2 expired locks, 1 fresh lock
        ShowSeat.objects.filter(pk=show_seats[0].pk).update(
            status=ShowSeat.StatusChoices.LOCKED,
            locked_by=user,
            locked_at=timezone.now() - timedelta(minutes=10),
        )
        ShowSeat.objects.filter(pk=show_seats[1].pk).update(
            status=ShowSeat.StatusChoices.LOCKED,
            locked_by=user,
            locked_at=timezone.now() - timedelta(minutes=10),
        )
        ShowSeat.objects.filter(pk=show_seats[2].pk).update(
            status=ShowSeat.StatusChoices.LOCKED,
            locked_by=user,
            locked_at=timezone.now(),  # Fresh lock — should NOT be released
        )

        released = release_expired_locks()
        self.assertEqual(released, 2)

        show_seats[0].refresh_from_db()
        self.assertEqual(show_seats[0].status, ShowSeat.StatusChoices.AVAILABLE)
        show_seats[1].refresh_from_db()
        self.assertEqual(show_seats[1].status, ShowSeat.StatusChoices.AVAILABLE)
        show_seats[2].refresh_from_db()
        self.assertEqual(show_seats[2].status, ShowSeat.StatusChoices.LOCKED)  # Untouched

    def test_sweeper_skips_booked_seats(self):
        """The sweeper never touches BOOKED seats."""
        _, _, show_seats = make_show_with_seats(1)
        ShowSeat.objects.filter(pk=show_seats[0].pk).update(
            status=ShowSeat.StatusChoices.BOOKED,
        )

        released = release_expired_locks()
        self.assertEqual(released, 0)

        show_seats[0].refresh_from_db()
        self.assertEqual(show_seats[0].status, ShowSeat.StatusChoices.BOOKED)
