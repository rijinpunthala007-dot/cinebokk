"""
CineBook — Theaters Admin
==========================
"""

from django.contrib import admin
from django.utils.html import format_html

from .models import City, Seat, SeatCategory, Screen, Theater


class ScreenInline(admin.TabularInline):
    model = Screen
    extra = 1
    fields = ("name", "total_capacity")
    show_change_link = True


class SeatCategoryInline(admin.TabularInline):
    model = SeatCategory
    extra = 0
    fields = ("category", "price")


class SeatInline(admin.TabularInline):
    model = Seat
    extra = 0
    fields = ("row_label", "seat_number", "category", "is_active")
    show_change_link = False
    max_num = 50     # Limit inline display — use list view for bulk


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "state", "is_active", "theater_count")
    list_filter = ("is_active", "state")
    search_fields = ("name", "state")
    list_editable = ("is_active",)
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("created_at", "updated_at")

    @admin.display(description="# Theaters")
    def theater_count(self, obj: City) -> int:
        return obj.theaters.count()


@admin.register(Theater)
class TheaterAdmin(admin.ModelAdmin):
    list_display = ("name", "city", "screen_count", "is_active", "created_at")
    list_filter = ("city", "is_active")
    search_fields = ("name", "city__name", "address")
    list_editable = ("is_active",)
    readonly_fields = ("created_at", "updated_at")
    inlines = [ScreenInline]

    @admin.display(description="# Screens")
    def screen_count(self, obj: Theater) -> int:
        return obj.screens.count()


@admin.register(Screen)
class ScreenAdmin(admin.ModelAdmin):
    list_display = ("name", "theater", "total_capacity", "seat_count", "created_at")
    list_filter = ("theater__city", "theater")
    search_fields = ("name", "theater__name")
    readonly_fields = ("created_at", "updated_at")
    inlines = [SeatCategoryInline]

    @admin.display(description="Active Seats")
    def seat_count(self, obj: Screen) -> int:
        return obj.seats.filter(is_active=True).count()


@admin.register(SeatCategory)
class SeatCategoryAdmin(admin.ModelAdmin):
    list_display = ("screen", "category", "price", "seat_count")
    list_filter = ("category", "screen__theater__city__name")
    search_fields = ("screen__name", "screen__theater__name")
    readonly_fields = ("created_at", "updated_at")

    @admin.display(description="# Seats")
    def seat_count(self, obj: SeatCategory) -> int:
        return obj.seats.filter(is_active=True).count()


@admin.register(Seat)
class SeatAdmin(admin.ModelAdmin):
    list_display = ("label", "screen", "category", "is_active")
    list_filter = ("category__category", "screen__theater__city__name", "is_active")
    search_fields = ("row_label", "screen__name", "screen__theater__name")
    list_editable = ("is_active",)
    readonly_fields = ("created_at", "updated_at")

    @admin.display(description="Seat")
    def label(self, obj: Seat) -> str:
        return obj.label
