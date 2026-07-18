"""
CineBook — Movies Serializers
==============================
"""

import re
from rest_framework import serializers
from .models import CastMember, Genre, Movie


class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ["id", "name"]


class CastMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = CastMember
        fields = ["id", "name", "character_name", "photo_url", "tmdb_person_id", "order"]


class MovieListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for the movie listing page."""

    genres = GenreSerializer(many=True, read_only=True)
    duration_display = serializers.CharField(read_only=True)

    class Meta:
        model = Movie
        fields = [
            "id", "title", "language", "rating", "release_date",
            "duration_minutes", "duration_display", "poster", "poster_url",
            "backdrop_url", "genres", "is_active",
        ]


class MovieDetailSerializer(serializers.ModelSerializer):
    """Full detail serializer — includes synopsis, cast, trailer."""

    genres = GenreSerializer(many=True, read_only=True)
    cast = CastMemberSerializer(source="cast_members", many=True, read_only=True)
    duration_display = serializers.CharField(read_only=True)
    trailer_youtube_key = serializers.SerializerMethodField()

    class Meta:
        model = Movie
        fields = [
            "id", "title", "description", "language", "rating",
            "release_date", "duration_minutes", "duration_display",
            "poster", "poster_url", "backdrop_url", "trailer_url",
            "trailer_youtube_url", "trailer_youtube_key", "tmdb_id",
            "cast_info", "cast", "genres", "is_active", "created_at",
        ]

    def get_trailer_youtube_key(self, obj: Movie) -> str | None:
        url = obj.trailer_youtube_url or obj.trailer_url
        if not url:
            return None
        match = re.search(r"(?:v=|\/embed\/|youtu\.be\/)([a-zA-Z0-9_-]{11})", url)
        return match.group(1) if match else None
