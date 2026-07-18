"""
CineBook — Accounts App Configuration
"""

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"
    verbose_name = "Accounts & Profiles"

    def ready(self) -> None:
        import apps.accounts.signals  # noqa: F401 — triggers signal registration
