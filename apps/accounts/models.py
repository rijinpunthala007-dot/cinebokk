"""
CineBook — Accounts Models
===========================
CustomerProfile extends Django's built-in User via a OneToOne relationship.
We do NOT substitute a custom User model to avoid migration complexity —
instead we extend via profile pattern, which is the production-safe approach
for adding fields without touching Django's auth internals.
"""

from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import gettext_lazy as _


class CustomerProfile(models.Model):
    """
    Extended profile for registered customers.
    Created automatically on user registration via a signal.
    """

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
        verbose_name=_("User"),
    )
    phone = models.CharField(
        _("Phone Number"),
        max_length=15,
        blank=True,
        default="",
    )
    city = models.CharField(
        _("Preferred City"),
        max_length=100,
        blank=True,
        default="",
        db_index=True,
    )
    avatar = models.ImageField(
        _("Profile Avatar"),
        upload_to="avatars/",
        null=True,
        blank=True,
    )
    date_of_birth = models.DateField(
        _("Date of Birth"),
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Customer Profile")
        verbose_name_plural = _("Customer Profiles")

    def __str__(self) -> str:
        return f"{self.user.get_full_name() or self.user.username} — {self.user.email}"
