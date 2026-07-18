"""CineBook — Movies API URLs"""

from django.urls import path
from . import views

app_name = "movies"

urlpatterns = [
    path("", views.MovieListView.as_view(), name="movie_list"),
    path("<int:pk>/", views.MovieDetailView.as_view(), name="movie_detail"),
    path("genres/", views.GenreListView.as_view(), name="genre_list"),
]

