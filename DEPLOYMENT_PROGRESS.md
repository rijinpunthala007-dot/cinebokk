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

## ✅ Task 9 — psycopg3 driver + Python version pin (post-deploy fix)
- **Symptom:** first Render deploy failed with `ImproperlyConfigured: Error loading psycopg2 or psycopg module`. Root cause: Render built on Python 3.14, which has no compatible prebuilt `psycopg2-binary==2.9.9` wheel (falls back to a source build that fails).
- **Fix (belt-and-suspenders):**
  1. Created `runtime.txt` = `python-3.12.7` to pin the build interpreter to a version with stable wheels.
  2. Swapped `psycopg2-binary==2.9.9` → `psycopg[binary]==3.2.3` (psycopg3) — broad prebuilt wheel coverage across Python 3.12–3.14, Django's recommended adapter going forward.
- **No settings change needed:** `ENGINE` stays `django.db.backends.postgresql` for all Postgres branches. Django 4.2+ auto-selects psycopg3 when installed, psycopg2 otherwise — same ENGINE string. `sslmode` in `OPTIONS` is a libpq keyword both drivers accept.
- Verified `dj-database-url` produces `django.db.backends.postgresql` for `postgres://` and `postgresql://` URLs (the branch Render uses).
- **Not smoke-tested locally** (Windows dev box uses SQLite; psycopg3 not installed there) — real validation is the next Render deploy.
- **Fallback if `runtime.txt` is ignored:** Render also reads a `PYTHON_VERSION` env var — set `PYTHON_VERSION=3.12.7` in the dashboard if needed.
- Files: `runtime.txt` (new), `requirements.txt`.

---

## ✅ Task 10 — Seed-on-deploy (no Shell access on Render free tier)
- Render free tier has no Shell, so one-off management commands were moved into `build.sh` to run on every deploy.
- **Idempotency audit:** core entities (movies, cities, theaters, screens, seats, genres) all use `get_or_create` — safe to re-run. Destructive wipe is gated behind `--clear` (NOT used in build.sh).
- **Seed-once guard (Option 1):** added `--skip-if-seeded` to `seed_movies` — no-ops if any `Movie` exists. So it seeds once on the first (empty-DB) deploy and is skipped on every deploy after. Live-tested against the 20-movie local DB: correctly skipped.
- **Pre-existing bug fixed:** `seed_movies.py` had an `IndentationError` (shows block, ~line 549) that made it fail to compile — would have crashed the first deploy. Fixed + compile-verified.
- **build.sh additions (after `migrate`):** `seed_movies --skip-if-seeded`, `sync_backdrops`, `apply_movie_media`. The latter two are naturally idempotent (file copy + URL writes) so they run unguarded every deploy.
- **Dead code removed:** `seed_data.py` (a near-duplicate of `seed_movies`, zero references anywhere) deleted along with its stale `.pyc`.
- Files: `build.sh`, `apps/movies/management/commands/seed_movies.py`, `apps/movies/management/commands/seed_data.py` (deleted).

### ⚠️ KNOWN LIMITATION — showtimes are dated relative to first deploy
- `seed_movies` builds shows for `date.today()` … `today + 3 days`, computed at seed time. Because of the seed-once guard, this runs **only on the first deploy** and never regenerates.
- **Consequence:** those showtimes are fixed to the first-deploy date. As days pass they become **past dates** and will not roll forward automatically. If the movie-list / shows view filters to upcoming showtimes, the app can appear to have no available shows a few days after deploy.
- **Fix if/when this becomes a problem:** add a lightweight "roll shows forward" management command (delete/rebuild only future-dated shows, or shift existing show `start_time`/`date` to the current window) and either run it manually via a redeploy step or schedule it with `django-crontab`. This is a *refresh*, NOT a re-seed — do not use `--clear` or drop the seed-once guard.

---

## Summary flags
- **Total static asset size: 9.0 MB** — well under the 100MB concern. Safe to commit to git for Render deploy.
- **MySQL-specific SQL:** none needing manual attention (only `charset`/`sql_mode` OPTIONS, already gated in the MySQL branch).
- **Postgres driver:** psycopg3 (`psycopg[binary]>=3.2.10,<3.3`), Python pinned to 3.12.7 via `runtime.txt`. `DATABASE_URL` parsing confirmed → correct `postgresql` ENGINE. Local connection not testable on the Windows/SQLite dev box — validated on Render deploy.
- **Seed-on-deploy:** guarded one-time seed via `build.sh`. Showtimes dated to first deploy and do NOT roll forward automatically (see Task 10 limitation above).
- **Repo is now a git repository** — `.gitignore` in place; `.env`, `db.sqlite3`, `.claude/`, `staticfiles/`, local `backdrops/`+`posters/` source art all excluded. Ready for `git add .` + commit.
