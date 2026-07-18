# Render Free-Tier Deployment — Progress Tracker

Resume point for an interrupted session. Each task lists status, what changed, and files touched.

---

## ✅ Task 1 — Reclassify local media as static files
- Moved pre-seeded assets from `/media/{posters,cast,backdrops}/` → `/static/img/{posters,cast,backdrops}/`.
- Data migration rewrites DB-stored string paths `/media/` → `/static/img/` (reversible).
- Repointed DRF serializers from MEDIA `ImageField` → static `CharField(source=*.poster_url)`.
- Whole-codebase `/media/` sweep: only legitimate refs remain (migration logic + `MEDIA_URL` default).
- Verified: 20 poster_url + 7 backdrop_url + 48 photo_url flipped; 0 missing files on disk.
- Files: `apps/movies/migrations/0003_media_to_static_paths.py`, `apps/shows/serializers.py`, `apps/bookings/serializers.py`, `static/js/movie_detail.js`, `apps/movies/management/commands/sync_backdrops.py`, `apps/movies/models.py`.

## ✅ Task 2 — WhiteNoise
- Added `whitenoise==6.7.0` to requirements.
- `WhiteNoiseMiddleware` inserted immediately after `SecurityMiddleware`.
- `STORAGES["staticfiles"]` → `whitenoise.storage.CompressedManifestStaticFilesStorage`.
- `WHITENOISE_MAX_AGE = env.int(default=31536000)` (1 year).
- Files: `requirements.txt`, `cinebook/settings.py`.

## ✅ Task 3 — Environment-based settings (django-environ)
- Replaced `python-decouple` with `django-environ`.
- `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, DB creds, CORS/CSRF, throttle rates, JWT, seat-lock all from env.
- Zero hardcoded secrets/hosts in `settings.py`. TMDb NOT reintroduced.
- Verified: no `decouple/config/Csv` symbols remain; `manage.py check` clean.
- Files: `cinebook/settings.py`, `requirements.txt`, `.env.example`.

## ✅ Task 4 — Dual database (Postgres on Render, MySQL local)
- Added `psycopg2-binary==2.9.9` + `dj-database-url==2.2.0`.
- 4-tier resolution: `DATABASE_URL` → `USE_POSTGRES` → `USE_MYSQL` → SQLite fallback.
- Render branch adds `CONN_MAX_AGE` + `OPTIONS["sslmode"]="require"`.
- MySQL-specific SQL audit: ONLY `charset`/`sql_mode` in the MySQL connection OPTIONS (gated inside USE_MYSQL branch). No raw SQL / RawSQL / cursor / MySQL-only DDL anywhere. Safe for Postgres.
- Verified: `env.db_url()` parses `DATABASE_URL` → correct `postgresql` ENGINE + sslmode.
- Files: `cinebook/settings.py`, `requirements.txt`.

## ✅ Task 5 — gunicorn
- Added `gunicorn==23.0.0` to requirements.
- Files: `requirements.txt`.

## ✅ Task 6 — build.sh
- `set -o errexit -o pipefail -o nounset`; `pip install -r requirements.txt` → `collectstatic --noinput` → `migrate --noinput`.
- Validated with `bash -n`. collectstatic verified locally: 257 copied, 603 post-processed, manifest written.
- Files: `build.sh`.

## ✅ Task 7 — ALLOWED_HOSTS / CSRF for *.onrender.com
- `ALLOWED_HOSTS` appends `RENDER_EXTERNAL_HOSTNAME` (env).
- `CSRF_TRUSTED_ORIGINS` default `["https://*.onrender.com"]` + appends `https://{RENDER_EXTERNAL_HOSTNAME}`.
- `CORS_ALLOWED_ORIGIN_REGEXES` default `[r"^https://.*\.onrender\.com$"]`.
- `if not DEBUG`: proxy SSL header, SSL redirect, secure cookies, HSTS, nosniff.
- Verified with `RENDER_EXTERNAL_HOSTNAME=cinebook.onrender.com`: host + CSRF origin resolve correctly.
- Files: `cinebook/settings.py`.

## ✅ Task 8 — Verify seed/utility scripts against static locations
- `seed_movies.py`: no hardcoded media/static paths (poster/photo URLs set via migration / `apply_movie_media`). OK.
- `sync_backdrops.py`: copies `backdrops/` → `static/img/backdrops/`, writes `/static/img/backdrops/...` URLs. OK.
- `apply_movie_media.py`: manual `MOVIE_MEDIA` dict → `poster_url`/`trailer_youtube_url`, TMDb-free. OK.
- `download_cast_photos.py`: **DOES NOT EXIST** in the repo. Cast photos are already under `static/img/cast/` (47 files). No action needed — flagged so it isn't mistaken for a missing step.
- Static tree verified: posters 20, cast 47, backdrops 7; total `static/` = 9.0MB.

---

## Summary flags
- **Total static asset size: 9.0 MB** — well under the 100MB concern. Safe to commit to git for Render deploy.
- **MySQL-specific SQL:** none needing manual attention (only `charset`/`sql_mode` OPTIONS, already gated in the MySQL branch).
- **Local psycopg2 note:** `DATABASE_URL` parsing confirmed (correct `postgresql` ENGINE). A local connection load errors with `No module named 'psycopg2'` — expected, since `psycopg2-binary` is installed on Render (in requirements.txt) not on the Windows dev box. Not a defect.
- **Repo is not yet a git repository** — `git init` + commit required before connecting to Render.
