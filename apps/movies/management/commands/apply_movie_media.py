"""
CineBook — Apply Manual Movie Media Command
===========================================
Reads apps/movies/movie_media.py (MOVIE_MEDIA dict) and writes poster_url /
trailer_youtube_url directly onto matching Movie rows. No TMDb API call.

Empty ("") values are SKIPPED, so movies you haven't filled in yet keep their
existing value (or stay blank -> frontend monogram / "Watch on YouTube" fallback).

Usage:
    python manage.py apply_movie_media
    python manage.py apply_movie_media --overwrite   # also clear fields set to "" in the dict
"""

from django.core.management.base import BaseCommand

from apps.movies.models import Movie
from apps.movies.movie_media import MOVIE_MEDIA


class Command(BaseCommand):
    help = "Apply manually-entered poster/trailer URLs from movie_media.py to Movie rows."

    def add_arguments(self, parser):
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Also apply empty ('') values, clearing any existing poster/trailer "
                 "on those movies. Default skips empties so partial lists are safe.",
        )

    def handle(self, *args, **options):
        overwrite = options.get("overwrite", False)

        updated = 0
        posters_set = 0
        trailers_set = 0
        skipped_blank = 0
        missing_titles = []

        for title, media in MOVIE_MEDIA.items():
            movie = Movie.objects.filter(title=title).first()
            if not movie:
                missing_titles.append(title)
                continue

            changed = False
            poster = (media.get("poster_url") or "").strip()
            trailer = (media.get("trailer_youtube_url") or "").strip()

            if poster or overwrite:
                if movie.poster_url != poster:
                    movie.poster_url = poster
                    changed = True
                if poster:
                    posters_set += 1
            elif not poster:
                skipped_blank += 1

            if trailer or overwrite:
                if movie.trailer_youtube_url != trailer:
                    movie.trailer_youtube_url = trailer
                    changed = True
                if trailer:
                    trailers_set += 1

            if changed:
                movie.save(update_fields=["poster_url", "trailer_youtube_url"])
                updated += 1
                self.stdout.write(self.style.SUCCESS(f"  [OK] {title}"))

        self.stdout.write(self.style.SUCCESS(
            f"\n[DONE] Applied manual media.\n"
            f"   Movies updated:  {updated}\n"
            f"   Posters set:     {posters_set}\n"
            f"   Trailers set:    {trailers_set}\n"
            f"   Blank (skipped): {skipped_blank}   (still using placeholder fallback)\n"
        ))

        if missing_titles:
            self.stdout.write(self.style.WARNING(
                "\n[WARN] These MOVIE_MEDIA keys did not match any Movie.title "
                "(check spelling against seed_movies.py):"
            ))
            for t in missing_titles:
                self.stdout.write(self.style.WARNING(f"   - {t!r}"))
