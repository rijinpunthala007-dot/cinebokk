"""
CineBook — Theaters Models
============================
Models: City, Theater, Screen, SeatCategory, Seat

Design decisions:
- City is a proper normalised lookup table so the city selector can be
  driven by the DB (no hardcoded JS arrays).
- Theater.city is a FK to City — all queries filter by city slug or name.
- SeatCategory ties a price to a category (CLASSIC/PREMIUM/RECLINER) per Screen,
  not per Seat, to avoid redundant price updates when the price changes.
- Seat has a composite unique constraint on (screen, row_label, seat_number) at
  both the ORM and DB levels.
"""

from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _


class City(models.Model):
    """An Indian city where CineBook operates."""

    name = models.CharField(_("City Name"), max_length=100, unique=True)
    slug = models.SlugField(_("URL Slug"), max_length=120, unique=True)
    state = models.CharField(_("State"), max_length=100, blank=True, default="")
    is_active = models.BooleanField(
        _("Is Active"),
        default=True,
        db_index=True,
        help_text="Inactive cities are hidden from the city selector.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("City")
        verbose_name_plural = _("Cities")
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Theater(models.Model):
    """A physical cinema multiplex."""

    name = models.CharField(_("Theater Name"), max_length=255)
    city = models.ForeignKey(
        City,
        on_delete=models.PROTECT,
        related_name="theaters",
        verbose_name=_("City"),
    )
    address = models.TextField(_("Address"))
    amenities = models.JSONField(
        _("Amenities"),
        default=list,
        blank=True,
        help_text='e.g. ["Parking", "Food Court", "Wheelchair Access"]',
    )
    is_active = models.BooleanField(_("Is Active"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Theater")
        verbose_name_plural = _("Theaters")
        ordering = ["city__name", "name"]
        indexes = [
            models.Index(fields=["city", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} — {self.city.name}"


class Screen(models.Model):
    """A single screen (auditorium) within a theater."""

    theater = models.ForeignKey(
        Theater,
        on_delete=models.CASCADE,
        related_name="screens",
        verbose_name=_("Theater"),
    )
    name = models.CharField(
        _("Screen Name"),
        max_length=100,
        help_text='e.g. "Screen 1", "IMAX", "Screen A"',
    )
    total_capacity = models.PositiveIntegerField(
        _("Total Seat Capacity"),
        default=0,
        help_text="Auto-computed when seats are added; can be set manually.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Screen")
        verbose_name_plural = _("Screens")
        unique_together = [("theater", "name")]
        ordering = ["theater", "name"]

    def __str__(self) -> str:
        return f"{self.theater.name} — {self.name}"


class SeatCategory(models.Model):
    """
    A seat tier for a specific screen. Each screen can have up to 3 categories.
    Prices are per-screen, not global — a CLASSIC seat in a premium theater
    may cost more than a CLASSIC seat in a budget theater.
    """

    class CategoryChoices(models.TextChoices):
        CLASSIC = "CLASSIC", _("Classic")
        PREMIUM = "PREMIUM", _("Premium")
        RECLINER = "RECLINER", _("Recliner")

    screen = models.ForeignKey(
        Screen,
        on_delete=models.CASCADE,
        related_name="seat_categories",
        verbose_name=_("Screen"),
    )
    category = models.CharField(
        _("Category"),
        max_length=20,
        choices=CategoryChoices.choices,
    )
    price = models.DecimalField(
        _("Price (INR)"),
        max_digits=8,
        decimal_places=2,
        help_text="Price in Indian Rupees.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Seat Category")
        verbose_name_plural = _("Seat Categories")
        unique_together = [("screen", "category")]

    def __str__(self) -> str:
        return f"{self.screen} — {self.category} @ ₹{self.price}"


class Seat(models.Model):
    """
    A physical seat in a screen.
    row_label: letter (A, B, C, ...) — displayed to users
    seat_number: integer within the row (1, 2, 3, ...)
    """

    screen = models.ForeignKey(
        Screen,
        on_delete=models.CASCADE,
        related_name="seats",
        verbose_name=_("Screen"),
    )
    category = models.ForeignKey(
        SeatCategory,
        on_delete=models.PROTECT,
        related_name="seats",
        verbose_name=_("Category"),
    )
    row_label = models.CharField(
        _("Row"),
        max_length=5,
        help_text='Row identifier, e.g. "A", "B", "AA"',
    )
    seat_number = models.PositiveSmallIntegerField(_("Seat Number"))
    is_active = models.BooleanField(
        _("Is Active"),
        default=True,
        help_text="Inactive seats are hidden from the seat map (e.g., broken/reserved).",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Seat")
        verbose_name_plural = _("Seats")
        unique_together = [("screen", "row_label", "seat_number")]
        ordering = ["screen", "row_label", "seat_number"]
        indexes = [
            models.Index(fields=["screen", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.screen} — {self.row_label}{self.seat_number} ({self.category.category})"

    @property
    def label(self) -> str:
        """Display label used in seat maps, e.g. 'A5'."""
        return f"{self.row_label}{self.seat_number}"
