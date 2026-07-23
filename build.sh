#!/usr/bin/env bash
# CineBook — Render build script
# Runs on every deploy: install deps, collect static assets, apply migrations.
# Referenced by the Render service's "Build Command": ./build.sh
set -o errexit   # abort on first error
set -o pipefail
set -o nounset

pip install -r requirements.txt

# Collect all static files (CSS/JS + pre-seeded posters/cast/backdrops under
# static/img/) into STATIC_ROOT for WhiteNoise to serve.
python manage.py collectstatic --noinput

# Apply database migrations (includes the /media -> /static/img path migration).
python manage.py migrate --noinput

# ---------------------------------------------------------------------------
# Seed data — runs on every deploy, but guarded to be effectively one-time.
# Render free tier has no Shell access, so one-off commands must live here.
# ---------------------------------------------------------------------------

# Movies / cities / theaters / screens / seats / shows.
# --skip-if-seeded makes this a no-op once the DB already has movies, so it
# seeds once on the first deploy (empty DB) and is skipped thereafter.
python manage.py seed_movies --skip-if-seeded

# Copy 16:9 backdrop banners into static/img/backdrops/ and set backdrop_url.
# Idempotent (get_or_create-style file copy + URL write).
python manage.py sync_backdrops

# Apply manual poster/trailer URLs from MOVIE_MEDIA. Idempotent — skips blanks
# and only overwrites when values change.
python manage.py apply_movie_media

# Roll all movies' shows into the current 7-day window.
# Idempotent.
# Also pinged daily via POST /api/v1/internal/refresh-showtimes/ by an external
# cron service, since deploys alone don't happen often enough to keep this
# fresh (see DEPLOYMENT_PROGRESS.md).
python manage.py refresh_showtimes

# Create shows for any movies that were seeded without shows (the 13 formerly-
# "upcoming" movies). Idempotent — skips movies that already have shows.
python manage.py backfill_shows
