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
