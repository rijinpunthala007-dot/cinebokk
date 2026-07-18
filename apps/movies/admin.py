"""
CineBook — Movies Admin
========================
"""

from django.contrib import admin
from django.utils.html import format_html

from .models import CastMember, Genre, Movie


class CastMemberInline(admin.TabularInline):
    model = CastMember
    extra = 1
    fields = ("name", "character_name", "photo_url", "tmdb_person_id", "order")


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ("name", "movie_count", "created_at")
    search_fields = ("name",)
    readonly_fields = ("created_at", "updated_at")

    @admin.display(description="# Movies")
    def movie_count(self, obj: Genre) -> int:
        return obj.movies.filter(is_active=True).count()


@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = (
        "title", "language", "rating", "release_date",
        "duration_display", "tmdb_id", "is_active", "poster_preview", "created_at",
    )
    list_filter = ("language", "rating", "is_active", "genres", "release_date")
    search_fields = ("title", "description")
    filter_horizontal = ("genres",)
    readonly_fields = ("created_at", "updated_at", "poster_preview")
    list_editable = ("is_active",)
    date_hierarchy = "release_date"
    ordering = ("-release_date",)
    inlines = [CastMemberInline]

    fieldsets = (
        ("Core Info", {
            "fields": ("title", "language", "rating", "genres", "is_active", "tmdb_id"),
        }),
        ("Details", {
            "fields": ("description", "duration_minutes", "release_date", "cast_info"),
        }),
        ("Media", {
            "fields": ("poster", "poster_url", "backdrop_url", "poster_preview", "trailer_url", "trailer_youtube_url"),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    @admin.display(description="Duration")
    def duration_display(self, obj: Movie) -> str:
        return obj.duration_display

    @admin.display(description="Poster")
    def poster_preview(self, obj: Movie) -> str:
        url = obj.poster.url if obj.poster else obj.poster_url
        if url:
            return format_html('<img src="{}" height="60" style="border-radius:4px;"/>', url)
        return "—"


@admin.register(CastMember)
class CastMemberAdmin(admin.ModelAdmin):
    list_display = ("name", "character_name", "movie", "order", "tmdb_person_id")
    list_filter = ("movie__language",)
    search_fields = ("name", "character_name", "movie__title")
