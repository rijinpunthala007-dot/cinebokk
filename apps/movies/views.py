"""
CineBook — Movies API Views
============================
"""

import logging
from django.db.models import Q
from rest_framework import status
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .models import Genre, Movie
from .serializers import GenreSerializer, MovieDetailSerializer, MovieListSerializer

logger = logging.getLogger("apps.movies")


class MoviesReadThrottle(ScopedRateThrottle):
    """
    Read-only browsing throttle (movie lists, detail, genres).
    Uses the generous ``movies_read`` rate instead of the login-grade ``anon``
    cap, so rapid filter/chip clicks never trip 429. Applies per-scope to both
    anonymous and authenticated users.
    """

    scope = "movies_read"


class MovieListView(ListAPIView):
    """
    GET /api/v1/movies/
    List active movies with optional filtering by city, genre, language, and search.
    """

    serializer_class = MovieListSerializer
    permission_classes = [AllowAny]
    throttle_classes = [MoviesReadThrottle]

    def get_queryset(self):
        qs = Movie.objects.filter(is_active=True).prefetch_related("genres")

        # City filter — only show movies with active shows in the given city
        city = self.request.query_params.get("city", "").strip()
        if city:
            qs = qs.filter(shows__screen__theater__city__name__iexact=city, shows__is_active=True).distinct()

        # Genre filter
        genre_id = self.request.query_params.get("genre", "").strip()
        if genre_id:
            try:
                qs = qs.filter(genres__id=int(genre_id))
            except (ValueError, TypeError):
                pass

        # Language filter
        language = self.request.query_params.get("language", "").strip()
        if language:
            qs = qs.filter(language__iexact=language)

        # Rating filter
        rating = self.request.query_params.get("rating", "").strip().upper()
        if rating in Movie.RatingChoices.values:
            qs = qs.filter(rating=rating)

        # Text search
        search = self.request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(Q(title__icontains=search) | Q(description__icontains=search))

        return qs.order_by("-release_date")


class MovieDetailView(RetrieveAPIView):
    """GET /api/v1/movies/{id}/ — Full movie detail with prefetched cast."""

    serializer_class = MovieDetailSerializer
    permission_classes = [AllowAny]
    throttle_classes = [MoviesReadThrottle]
    queryset = Movie.objects.filter(is_active=True).prefetch_related("genres", "cast_members")


class GenreListView(ListAPIView):
    """GET /api/v1/movies/genres/ — All genres for the filter bar."""

    serializer_class = GenreSerializer
    permission_classes = [AllowAny]
    throttle_classes = [MoviesReadThrottle]
    queryset = Genre.objects.all().order_by("name")
    pagination_class = None     # Return all genres without pagination

