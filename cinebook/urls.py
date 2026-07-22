"""
CineBook URL Configuration
===========================
Main URL router. API routes are versioned under /api/v1/.
Frontend template views are served at the root.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

from apps.shows.views import RefreshShowtimesView

# Customise the admin site header
admin.site.site_header = "CineBook Admin"
admin.site.site_title = "CineBook"
admin.site.index_title = "Platform Administration"

urlpatterns = [
    # Django Admin
    path("admin/", admin.site.urls),

    # API v1 — versioned namespace
    path("api/v1/auth/", include("apps.accounts.urls", namespace="accounts")),
    path("api/v1/movies/", include("apps.movies.urls", namespace="movies")),
    path("api/v1/shows/", include("apps.shows.urls", namespace="shows")),
    path("api/v1/bookings/", include("apps.bookings.urls", namespace="bookings")),
    path("api/v1/dashboard/", include("apps.dashboard.urls", namespace="dashboard")),
    path("api/v1/cities/", include("apps.theaters.urls", namespace="theaters")),

    # Internal — pinged by an external cron service (see DEPLOYMENT_PROGRESS.md)
    path("api/v1/internal/refresh-showtimes/", RefreshShowtimesView.as_view(), name="refresh_showtimes"),

    # Frontend template views
    path("", include("apps.movies.frontend_urls")),
    path("bookings/", include("apps.bookings.frontend_urls")),
    path("accounts/", include("apps.accounts.frontend_urls")),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Custom error handlers
handler404 = "cinebook.views.handler404"
handler500 = "cinebook.views.handler500"
