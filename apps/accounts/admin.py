"""
CineBook — Accounts Admin
==========================
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from .models import CustomerProfile


class CustomerProfileInline(admin.StackedInline):
    """Embed CustomerProfile fields directly in the User admin view."""

    model = CustomerProfile
    can_delete = False
    verbose_name_plural = "Customer Profile"
    fields = ("phone", "city", "avatar", "date_of_birth")
    extra = 0


class CineBookUserAdmin(BaseUserAdmin):
    """Extend the default User admin with the embedded profile."""

    inlines = [CustomerProfileInline]
    list_display = ("username", "email", "first_name", "last_name", "is_staff", "is_active", "date_joined")
    list_filter = ("is_staff", "is_active", "date_joined")
    search_fields = ("username", "email", "first_name", "last_name")
    ordering = ("-date_joined",)


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "phone", "city", "date_of_birth", "updated_at")
    search_fields = ("user__username", "user__email", "phone", "city")
    list_filter = ("city",)
    readonly_fields = ("created_at", "updated_at")
    raw_id_fields = ("user",)


# Re-register User with the extended admin
admin.site.unregister(User)
admin.site.register(User, CineBookUserAdmin)
