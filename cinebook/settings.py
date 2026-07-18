"""
CineBook Django Settings
========================
Environment-driven configuration via django-environ.
Local dev uses SQLite or MySQL; Render production uses PostgreSQL (DATABASE_URL).
Never hardcode secrets — all sensitive values come from the environment / .env.
"""

from pathlib import Path
from datetime import timedelta

import environ

# ---------------------------------------------------------------------------
# Paths & environment
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    USE_MYSQL=(bool, False),
    USE_POSTGRES=(bool, False),
)
# Load .env if present (local dev). On Render, real env vars take precedence.
environ.Env.read_env(BASE_DIR / ".env")

# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------
SECRET_KEY: str = env("SECRET_KEY")
DEBUG: bool = env.bool("DEBUG", default=False)
ALLOWED_HOSTS: list[str] = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

# Render provides the external hostname at runtime; trust it automatically so a
# newly-created service works before ALLOWED_HOSTS is manually updated.
RENDER_EXTERNAL_HOSTNAME = env("RENDER_EXTERNAL_HOSTNAME", default="")
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

# ---------------------------------------------------------------------------
# Installed Applications
# ---------------------------------------------------------------------------
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_crontab",
]

LOCAL_APPS = [
    "apps.accounts",
    "apps.movies",
    "apps.theaters",
    "apps.shows",
    "apps.bookings",
    "apps.dashboard",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",          # CORS — must be first
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",     # Serve static files in prod
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",      # CSRF — always on
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "cinebook.urls"

# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "cinebook.wsgi.application"
ASGI_APPLICATION = "cinebook.asgi.application"

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
# Priority:
#   1. DATABASE_URL present  -> parse it (Render Postgres in production)
#   2. USE_POSTGRES=True     -> build Postgres config from discrete env vars
#   3. USE_MYSQL=True        -> local MySQL
#   4. otherwise             -> SQLite (zero-config local dev)
if env("DATABASE_URL", default=""):
    DATABASES = {
        "default": env.db_url(
            "DATABASE_URL",
            # conn_max_age keeps connections warm; ssl_require for managed PG
        ),
    }
    DATABASES["default"]["CONN_MAX_AGE"] = env.int("DB_CONN_MAX_AGE", default=600)
    DATABASES["default"].setdefault("OPTIONS", {})
    if env.bool("DB_SSL_REQUIRE", default=True):
        DATABASES["default"]["OPTIONS"]["sslmode"] = "require"

elif env.bool("USE_POSTGRES", default=False):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env("DB_NAME", default="cinebook_db"),
            "USER": env("DB_USER", default="postgres"),
            "PASSWORD": env("DB_PASSWORD", default=""),
            "HOST": env("DB_HOST", default="127.0.0.1"),
            "PORT": env("DB_PORT", default="5432"),
            "CONN_MAX_AGE": env.int("DB_CONN_MAX_AGE", default=600),
        }
    }

elif env.bool("USE_MYSQL", default=False):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": env("DB_NAME", default="cinebook_db"),
            "USER": env("DB_USER", default="root"),
            "PASSWORD": env("DB_PASSWORD", default=""),
            "HOST": env("DB_HOST", default="127.0.0.1"),
            "PORT": env("DB_PORT", default="3306"),
            "OPTIONS": {
                "charset": "utf8mb4",
                "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
            },
        }
    }

else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
            # SQLite test isolation — use in-memory DB for tests
            "TEST": {
                "NAME": ":memory:",
            },
        }
    }

# ---------------------------------------------------------------------------
# Password Validation
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"   # IST — standard for BookMyShow-style apps
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static & Media Files
# ---------------------------------------------------------------------------
STATIC_URL = env("STATIC_URL", default="/static/")
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

# WhiteNoise: compressed + hashed manifest storage for cache-busting, and serve
# collectstatic output directly from the WSGI app (no nginx/S3 needed on Render).
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
# Cache pre-seeded poster/cast/backdrop art aggressively (1 year). Hashed
# filenames from the manifest storage make this safe.
WHITENOISE_MAX_AGE = env.int("WHITENOISE_MAX_AGE", default=31536000)

# MEDIA is retained only for any future user uploads in local dev. On Render the
# disk is ephemeral, so nothing durable should live here — pre-seeded assets are
# static (see /static/img/).
MEDIA_URL = env("MEDIA_URL", default="/media/")
MEDIA_ROOT = BASE_DIR / "media"

# ---------------------------------------------------------------------------
# Default Primary Key
# ---------------------------------------------------------------------------
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",  # Admin / browser
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": env("ANON_THROTTLE_RATE", default="120/min"),
        "user": env("USER_THROTTLE_RATE", default="300/min"),
        "login": "5/min",        # named throttle for login endpoint
        # Read-only browsing (movie lists, genres, showtimes) — generous:
        # clicking through filters must never hit the login-grade anon cap.
        "movies_read": env("MOVIES_READ_THROTTLE_RATE", default="300/min"),
    },
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "EXCEPTION_HANDLER": "cinebook.exceptions.cinebook_exception_handler",
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
}

# ---------------------------------------------------------------------------
# Simple JWT
# ---------------------------------------------------------------------------
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=env.int("JWT_ACCESS_TOKEN_LIFETIME_MINUTES", default=60)
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(
        days=env.int("JWT_REFRESH_TOKEN_LIFETIME_DAYS", default=7)
    ),
    "ROTATE_REFRESH_TOKENS": True,           # Issue new refresh on each use
    "BLACKLIST_AFTER_ROTATION": True,        # Revoke old refresh tokens
    "ALGORITHM": "HS256",
    "AUTH_HEADER_TYPES": ("Bearer",),
    "TOKEN_OBTAIN_SERIALIZER": "apps.accounts.serializers.CineBookTokenObtainPairSerializer",
}

# ---------------------------------------------------------------------------
# CORS (django-cors-headers)
# ---------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS: list[str] = env.list(
    "CORS_ALLOWED_ORIGINS",
    default=["http://localhost:8000", "http://127.0.0.1:8000"],
)
# Allow any Render subdomain for the deployed frontend/API without hardcoding
# the exact service name (not known until the service is created).
CORS_ALLOWED_ORIGIN_REGEXES = env.list(
    "CORS_ALLOWED_ORIGIN_REGEXES",
    default=[r"^https://.*\.onrender\.com$"],
)
# Never use CORS_ALLOW_ALL_ORIGINS=True in any real environment
CORS_ALLOW_CREDENTIALS = True

# ---------------------------------------------------------------------------
# CSRF
# ---------------------------------------------------------------------------
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_HTTPONLY = False     # JS needs to read CSRF for AJAX
SESSION_COOKIE_HTTPONLY = True

# Trusted origins for unsafe (POST/PUT/DELETE) requests over HTTPS. Accept the
# wildcard Render domain plus any explicitly configured origins. Replace with the
# exact service URL once known (e.g. https://cinebook.onrender.com).
CSRF_TRUSTED_ORIGINS: list[str] = env.list(
    "CSRF_TRUSTED_ORIGINS",
    default=["https://*.onrender.com"],
)
if RENDER_EXTERNAL_HOSTNAME:
    CSRF_TRUSTED_ORIGINS.append(f"https://{RENDER_EXTERNAL_HOSTNAME}")

# ---------------------------------------------------------------------------
# Security Headers (production hardening)
# ---------------------------------------------------------------------------
if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    # Render terminates TLS at its edge and forwards X-Forwarded-Proto; without
    # this Django sees http and would redirect-loop / mis-set secure cookies.
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# ---------------------------------------------------------------------------
# CineBook Domain Settings
# ---------------------------------------------------------------------------
SEAT_LOCK_MINUTES: int = env.int("SEAT_LOCK_MINUTES", default=5)

# ---------------------------------------------------------------------------
# Django Crontab (Celery-free background tasks)
# ---------------------------------------------------------------------------
CRONJOBS = [
    # Run expired-lock sweeper every minute
    ("* * * * *", "apps.shows.cron.release_expired_locks", ">> /tmp/cinebook_cron.log 2>&1"),
]

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{levelname}] {asctime} {name} {module}:{lineno} — {message}",
            "style": "{",
        },
        "simple": {
            "format": "[{levelname}] {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": BASE_DIR / "logs" / "cinebook.log",
            "maxBytes": 10 * 1024 * 1024,  # 10 MB
            "backupCount": 5,
            "formatter": "verbose",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": True,
        },
        "cinebook": {
            "handlers": ["console", "file"],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": False,
        },
        "apps": {
            "handlers": ["console", "file"],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": False,
        },
    },
}

# Ensure logs directory exists
(BASE_DIR / "logs").mkdir(exist_ok=True)
