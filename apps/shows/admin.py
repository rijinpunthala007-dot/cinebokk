"""
CineBook — Shows Admin
=======================
"""

from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html

from .models import Show, ShowSeat


class ShowSeatInline(admin.TabularInline):
    model = ShowSeat
    extra = 0
    fields = ("seat", "status", "locked_by", "locked_at")
    readonly_fields = ("locked_at",)
    show_change_link = False
    can_delete = False
    max_num = 0     # No adding seats via inline — they're bulk-created


@admin.register(Show)
class ShowAdmin(admin.ModelAdmin):
    list_display = (
        "movie_title", "screen_name", "start_time", "language",
        "occupancy_display", "is_active", "bookable_badge",
    )
    list_filter = ("is_active", "language", "date", "screen__theater__city")
    search_fields = ("movie__title", "screen__name", "screen__theater__name")
    date_hierarchy = "date"
    readonly_fields = ("end_time", "date", "created_at", "updated_at")
    ordering = ("-start_time",)
    actions = ["mark_inactive"]

    fieldsets = (
        ("Show Info", {
            "fields": ("movie", "screen", "language", "is_active"),
        }),
        ("Timing", {
            "fields": ("start_time", "end_time", "date"),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    @admin.display(description="Movie")
    def movie_title(self, obj: Show) -> str:
        return obj.movie.title

    @admin.display(description="Screen")
    def screen_name(self, obj: Show) -> str:
        return str(obj.screen)

    @admin.display(description="Occupancy")
    def occupancy_display(self, obj: Show) -> str:
        total = obj.show_seats.count()
        if total == 0:
            return "No seats"
        booked = obj.show_seats.filter(status=ShowSeat.StatusChoices.BOOKED).count()
        pct = (booked / total) * 100
        return f"{booked}/{total} ({pct:.0f}%)"

    @admin.display(description="Bookable", boolean=True)
    def bookable_badge(self, obj: Show) -> bool:
        return obj.is_bookable

    @admin.action(description="Mark selected shows as inactive")
    def mark_inactive(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} show(s) marked as inactive.")


@admin.register(ShowSeat)
class ShowSeatAdmin(admin.ModelAdmin):
    list_display = ("show", "seat_label", "status", "locked_by", "locked_at", "lock_expired_badge")
    list_filter = ("status", "show__date", "show__screen__theater__city")
    search_fields = ("show__movie__title", "seat__row_label")
    readonly_fields = ("created_at", "updated_at", "lock_expired_badge")
    actions = ["release_expired_locks_action"]

    @admin.display(description="Seat")
    def seat_label(self, obj: ShowSeat) -> str:
        return obj.seat.label

    @admin.display(description="Lock Expired", boolean=True)
    def lock_expired_badge(self, obj: ShowSeat) -> bool:
        return obj.is_lock_expired

    @admin.action(description="Release expired locks for selected seats")
    def release_expired_locks_action(self, request, queryset):
        from apps.shows.cron import release_expired_locks
        count = release_expired_locks()
        self.message_user(request, f"Released {count} expired lock(s).")
