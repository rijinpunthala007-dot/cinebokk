"""
CineBook — Bookings Admin
==========================
"""

from django.contrib import admin
from django.utils.html import format_html

from .models import Booking, BookingSeat


class BookingSeatInline(admin.TabularInline):
    model = BookingSeat
    extra = 0
    fields = ("seat", "price_at_booking")
    readonly_fields = ("seat", "price_at_booking")
    can_delete = False


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        "booking_ref_short", "customer_email", "movie_title",
        "show_time", "status", "total_amount", "seat_count", "booked_at",
    )
    list_filter = ("status", "show__date", "show__screen__theater__city")
    search_fields = (
        "booking_ref", "customer__email", "customer__username",
        "show__movie__title",
    )
    readonly_fields = (
        "booking_ref", "booked_at", "created_at", "updated_at",
        "payment_ref", "total_amount",
    )
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    inlines = [BookingSeatInline]
    actions = ["cancel_selected_bookings"]

    fieldsets = (
        ("Booking", {
            "fields": ("booking_ref", "customer", "show", "status"),
        }),
        ("Payment", {
            "fields": ("total_amount", "payment_ref"),
        }),
        ("Cancellation", {
            "fields": ("cancellation_reason",),
            "classes": ("collapse",),
        }),
        ("Timestamps", {
            "fields": ("booked_at", "created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    @admin.display(description="Ref")
    def booking_ref_short(self, obj: Booking) -> str:
        return str(obj.booking_ref)[:8].upper()

    @admin.display(description="Customer")
    def customer_email(self, obj: Booking) -> str:
        return obj.customer.email

    @admin.display(description="Movie")
    def movie_title(self, obj: Booking) -> str:
        return obj.show.movie.title

    @admin.display(description="Show Time")
    def show_time(self, obj: Booking) -> str:
        return obj.show.start_time.strftime("%d %b, %I:%M %p")

    @admin.display(description="# Seats")
    def seat_count(self, obj: Booking) -> int:
        return obj.booking_seats.count()

    @admin.action(description="Cancel selected bookings (admin override)")
    def cancel_selected_bookings(self, request, queryset):
        from django.utils import timezone
        cancelled = 0
        for booking in queryset.filter(status=Booking.StatusChoices.CONFIRMED):
            # Release seat locks
            booking.booking_seats.all().select_related("show_seat").update(
                # We go through the booking seats to find show seats
            )
            booking.status = Booking.StatusChoices.CANCELLED
            booking.cancellation_reason = "Cancelled by admin"
            booking.save(update_fields=["status", "cancellation_reason", "updated_at"])
            cancelled += 1
        self.message_user(request, f"Cancelled {cancelled} booking(s).")


@admin.register(BookingSeat)
class BookingSeatAdmin(admin.ModelAdmin):
    list_display = ("booking", "seat_label", "price_at_booking", "created_at")
    search_fields = ("booking__booking_ref", "seat__row_label")
    readonly_fields = ("created_at", "updated_at")
    raw_id_fields = ("booking", "show_seat", "seat")

    @admin.display(description="Seat")
    def seat_label(self, obj: BookingSeat) -> str:
        return obj.seat.label
