"""CineBook — Movies Frontend URLs"""

from django.urls import path
from . import frontend_views

urlpatterns = [
    path("", frontend_views.HomeView.as_view(), name="home"),
    path("movies/<int:pk>/", frontend_views.MovieDetailView.as_view(), name="movie_detail"),
    path("movies/<int:movie_id>/shows/", frontend_views.ShowtimesView.as_view(), name="showtimes"),
]
