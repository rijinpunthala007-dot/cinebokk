"""
CineBook — Movies Models
=========================
Models: Genre, Movie, CastMember
Language and Genre are normalised lookup tables to allow clean filtering.
"""

import json
from django.db import models
from django.utils.translation import gettext_lazy as _


class Genre(models.Model):
    """Movie genre (Action, Comedy, Drama, etc.)."""

    name = models.CharField(_("Genre Name"), max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Genre")
        verbose_name_plural = _("Genres")
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Movie(models.Model):
    """
    Core movie entity.
    - poster: legacy ImageField (upload_to posters/); pre-seeded artwork now lives
      under /static/img/posters/ and is referenced via poster_url instead
    - poster_url / backdrop_url: image URLs (local /static/img/... or remote)
    - trailer_youtube_url: direct YouTube trailer link
    - tmdb_id: unique TMDb identifier
    - cast_info: JSON field for legacy/flexible cast data
    - language: stored as a plain string (denormalised) for simpler filtering
    """

    class RatingChoices(models.TextChoices):
        U = "U", _("U — Universal")
        UA = "UA", _("UA — Parental Guidance")
        A = "A", _("A — Adults Only")
        S = "S", _("S — Special Audience")

    title = models.CharField(_("Title"), max_length=255, db_index=True)
    description = models.TextField(_("Synopsis"), blank=True, default="")
    duration_minutes = models.PositiveIntegerField(
        _("Duration (minutes)"),
        help_text="Runtime in minutes. Must be > 0.",
    )
    language = models.CharField(_("Language"), max_length=50, db_index=True)
    release_date = models.DateField(_("Release Date"), db_index=True)
    poster = models.ImageField(
        _("Poster Image"),
        upload_to="posters/",
        null=True,
        blank=True,
    )
    poster_url = models.URLField(_("Poster URL"), null=True, blank=True)
    backdrop_url = models.URLField(_("Backdrop URL"), null=True, blank=True)
    trailer_url = models.URLField(
        _("Trailer URL"),
        blank=True,
        default="",
        help_text="Legacy YouTube embed URL or similar.",
    )
    trailer_youtube_url = models.URLField(_("YouTube Trailer URL"), null=True, blank=True)
    tmdb_id = models.IntegerField(_("TMDb ID"), null=True, blank=True, unique=True)
    cast_info = models.JSONField(
        _("Cast Information"),
        default=list,
        blank=True,
        help_text='List of {"name": "...", "role": "...", "image": "..."} objects.',
    )
    rating = models.CharField(
        _("Rating"),
        max_length=5,
        choices=RatingChoices.choices,
        default=RatingChoices.UA,
    )
    genres = models.ManyToManyField(
        Genre,
        related_name="movies",
        blank=True,
        verbose_name=_("Genres"),
    )
    is_active = models.BooleanField(
        _("Is Active"),
        default=True,
        db_index=True,
        help_text="Inactive movies are hidden from the public listing.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Movie")
        verbose_name_plural = _("Movies")
        ordering = ["-release_date"]
        indexes = [
            models.Index(fields=["language", "is_active"]),
            models.Index(fields=["release_date", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.language}, {self.release_date.year})"

    @property
    def duration_display(self) -> str:
        """Human-readable duration, e.g. '2h 30m'."""
        hours, minutes = divmod(self.duration_minutes, 60)
        if hours and minutes:
            return f"{hours}h {minutes}m"
        elif hours:
            return f"{hours}h"
        return f"{minutes}m"


class CastMember(models.Model):
    """Structured cast member record populated from TMDb or manual entry."""

    movie = models.ForeignKey(
        Movie,
        on_delete=models.CASCADE,
        related_name="cast_members",
        verbose_name=_("Movie"),
    )
    name = models.CharField(_("Actor Name"), max_length=255)
    character_name = models.CharField(_("Character Name"), max_length=255, blank=True, default="")
    photo_url = models.URLField(_("Photo URL"), null=True, blank=True)
    tmdb_person_id = models.IntegerField(_("TMDb Person ID"), null=True, blank=True)
    order = models.PositiveIntegerField(_("Display Order"), default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Cast Member")
        verbose_name_plural = _("Cast Members")
        ordering = ["order", "name"]

    def __str__(self) -> str:
        return f"{self.name} as {self.character_name or 'Cast'} in {self.movie.title}"
