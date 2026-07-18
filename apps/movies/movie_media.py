"""
CineBook — Manual Movie Media (posters + trailers)
==================================================
Single source of truth for poster/trailer URLs, entered by hand.

Paste real URLs below, then run:

    python manage.py apply_movie_media

Rules:
  - Keys MUST exactly match Movie.title in the database (copy from seed_movies.py).
  - Leave a value as "" (empty string) for anything not filled in yet. The apply
    command SKIPS empty values, so the frontend monogram placeholder / "Watch on
    YouTube" fallback keeps working for movies you haven't filled in.
  - poster_url:            a full https:// image URL (jpg/png/webp).
  - trailer_youtube_url:   a full https://www.youtube.com/watch?v=KEY URL.
                           (The detail page extracts the ?v= key for the embed.)
"""

# title -> {"poster_url": "...", "trailer_youtube_url": "..."}
MOVIE_MEDIA = {
    # --- Malayalam (7) ---
    "Bazooka": {
        "poster_url": "",
        "trailer_youtube_url": "",
    },
    "Lokah Chapter 1: Chandra": {
        "poster_url": "",
        "trailer_youtube_url": "",
    },
    "Hridayapoorvam": {
        "poster_url": "",
        "trailer_youtube_url": "",
    },
    "Identity": {
        "poster_url": "",
        "trailer_youtube_url": "",
    },
    "Kalamkaval": {
        "poster_url": "",
        "trailer_youtube_url": "",
    },
    "Kathanar: The Wild Sorcerer": {
        "poster_url": "",
        "trailer_youtube_url": "",
    },
    "Tiki Taka": {
        "poster_url": "",
        "trailer_youtube_url": "",
    },

    # --- Hindi (7) ---
    "Dhamaal 4": {
        "poster_url": "",
        "trailer_youtube_url": "",
    },
    "Dhurandhar": {
        "poster_url": "",
        "trailer_youtube_url": "",
    },
    "Border 2": {
        "poster_url": "",
        "trailer_youtube_url": "",
    },
    "Cocktail 2": {
        "poster_url": "",
        "trailer_youtube_url": "",
    },
    "Main Vaapas Aaunga": {
        "poster_url": "",
        "trailer_youtube_url": "",
    },
    "Baby Do Die Do": {
        "poster_url": "",
        "trailer_youtube_url": "",
    },
    "Karuppu": {
        "poster_url": "",
        "trailer_youtube_url": "",
    },

    # --- English (6) ---
    "Spider-Man: Brand New Day": {
        "poster_url": "",
        "trailer_youtube_url": "",
    },
    "Moana (2026)": {
        "poster_url": "",
        "trailer_youtube_url": "",
    },
    "Toy Story 5": {
        "poster_url": "",
        "trailer_youtube_url": "",
    },
    "Avatar: Fire and Ash": {
        "poster_url": "",
        "trailer_youtube_url": "",
    },
    "The Odyssey": {
        "poster_url": "",
        "trailer_youtube_url": "",
    },
    "Supergirl": {
        "poster_url": "",
        "trailer_youtube_url": "",
    },
}
