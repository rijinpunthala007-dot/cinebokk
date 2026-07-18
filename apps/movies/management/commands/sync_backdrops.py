"""
CineBook — Backdrops Sync Command
===================================
Scans the `backdrops/` folder for 16:9 banner photos, copies them to `static/img/backdrops/`,
and links `backdrop_url` to the respective Movie records in the database.

One-time local setup script (run before deploy). Assets live under static/ so
collectstatic + WhiteNoise serve them in production.

Usage:
    python manage.py sync_backdrops
"""

import os
import re
import shutil
import logging
from django.core.management.base import BaseCommand
from apps.movies.models import Movie

logger = logging.getLogger("management")


def normalize_title(text: str) -> str:
    """Normalize string by converting to lowercase and stripping non-alphanumeric characters."""
    return re.sub(r'[^a-z0-9]', '', text.lower())


ALIASES = {
    "loakh": "lokah",
    "moana2": "moana",
    "spiderman": "spiderman",
    "avatarfireandash": "avatar",
}


class Command(BaseCommand):
    help = "Sync 16:9 backdrop banner photos from backdrops/ folder into static/img/backdrops/ and database."

    def handle(self, *args, **options):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
        src_dir = os.path.join(base_dir, "backdrops")
        dst_dir = os.path.join(base_dir, "static", "img", "backdrops")

        os.makedirs(src_dir, exist_ok=True)
        os.makedirs(dst_dir, exist_ok=True)

        files = [f for f in os.listdir(src_dir) if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))]
        if not files:
            self.stdout.write(self.style.WARNING(
                f"\nNo 16:9 backdrop images found in {src_dir}.\n"
                f"Add your 16:9 movie photos to the 'backdrops' folder and run this command again.\n"
            ))
            return

        self.stdout.write(f"Syncing {len(files)} backdrop images...\n")
        movies = list(Movie.objects.all())
        synced_count = 0

        for fname in files:
            clean_name = fname.replace(" ", "_")
            src_path = os.path.join(src_dir, fname)
            dst_path = os.path.join(dst_dir, clean_name)
            shutil.copy2(src_path, dst_path)

            raw_stem = os.path.splitext(fname)[0]
            stem_norm = normalize_title(raw_stem)
            
            # Alias lookup
            for alias_key, alias_val in ALIASES.items():
                if alias_key in stem_norm:
                    stem_norm = stem_norm.replace(alias_key, alias_val)

            matched_movie = None
            for m in movies:
                m_norm = normalize_title(m.title)
                # Check for mutual substring containment
                if stem_norm in m_norm or m_norm in stem_norm:
                    matched_movie = m
                    break
                # Partial key matching (e.g. avatar, spiderman, moana, odysseys, kathanar)
                keys = [k for k in m_norm.split() if len(k) > 3]
                if any(k in stem_norm for k in keys):
                    matched_movie = m
                    break

            if matched_movie:
                rel_url = f"/static/img/backdrops/{clean_name}"
                matched_movie.backdrop_url = rel_url
                matched_movie.save()
                synced_count += 1
                self.stdout.write(self.style.SUCCESS(f"  [OK] Matched '{fname}' -> {matched_movie.title} ({rel_url})"))
            else:
                self.stdout.write(self.style.WARNING(f"  [WARN] '{fname}' -- could not automatically match to a movie title"))

        self.stdout.write(self.style.SUCCESS(f"\n[SUCCESS] Synced {synced_count} 16:9 backdrop banners!"))
