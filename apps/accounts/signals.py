"""
CineBook — Accounts Signals
==============================
Auto-create a CustomerProfile whenever a new User is registered.
This ensures the profile always exists — no null-check needed in views.
"""

import logging
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger("apps.accounts")


@receiver(post_save, sender=User)
def create_customer_profile(sender, instance: User, created: bool, **kwargs) -> None:
    """Create a CustomerProfile when a new User is registered."""
    if created:
        from apps.accounts.models import CustomerProfile
        CustomerProfile.objects.get_or_create(user=instance)
        logger.debug("CustomerProfile created for user: %s", instance.username)


@receiver(post_save, sender=User)
def save_customer_profile(sender, instance: User, **kwargs) -> None:
    """Ensure the profile is saved when the User is saved."""
    if hasattr(instance, "profile"):
        instance.profile.save()
