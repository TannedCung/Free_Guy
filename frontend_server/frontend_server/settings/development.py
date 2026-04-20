"""
Django development settings for frontend_server project.

Imports base settings and adds development-specific overrides:
  - DEBUG = True
  - SQLite database (or DATABASE_URL if set)
  - Verbose logging to console and rotating file
  - Relaxed security (no HTTPS cookies)

Usage: DJANGO_ENV=development (the default)
"""

import os

import dj_database_url

from .base import *  # noqa: F401, F403

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# Serve the React SPA bundle via whitenoise in dev (when running Django on port 8000
# directly rather than via the Vite dev server on port 3000).
INSTALLED_APPS = ["whitenoise.runserver_nostatic"] + INSTALLED_APPS  # noqa: F405
MIDDLEWARE = [  # noqa: F405
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
] + [m for m in MIDDLEWARE if m != "django.middleware.security.SecurityMiddleware"]  # noqa: F405
WHITENOISE_ROOT = REACT_DIST_DIR  # noqa: F405

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0", "*"]

# Trust forwarded headers from nginx (or the Vite dev proxy in local-only mode)
# so Django builds correct absolute URLs and OAuth redirect_uris.
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = None  # HTTP only in dev — don't force HTTPS

# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

_database_url = os.environ.get("DATABASE_URL")
if _database_url:
    DATABASES = {"default": dj_database_url.parse(_database_url)}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": os.path.join(BASE_DIR, "db.sqlite3"),  # noqa: F405
        }
    }

# CORS — allow all local origins in dev
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

# CSRF — local defaults + any extra origin declared in the environment.
# Add a comma-separated list to CSRF_TRUSTED_ORIGINS in .env for tunnels
# (ngrok, localtunnel, etc.) or any other external origin you need in dev.
# DJANGO_SITE_DOMAIN is automatically included when set.
_csrf_trusted_origins = [
    "http://localhost",
    "http://localhost:80",
    "http://localhost:3000",
    "http://localhost:8000",
    "http://127.0.0.1",
    "http://127.0.0.1:80",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8000",
]
_extra_origins = os.environ.get("CSRF_TRUSTED_ORIGINS", "")
if _extra_origins:
    _csrf_trusted_origins += [o.strip() for o in _extra_origins.split(",") if o.strip()]
_site_domain = os.environ.get("DJANGO_SITE_DOMAIN", "")
if _site_domain:
    _csrf_trusted_origins.append(f"https://{_site_domain}")
CSRF_TRUSTED_ORIGINS = _csrf_trusted_origins

# Cookie security — disable HTTPS enforcement in local dev
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Verbose logging for development
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "%(asctime)s %(levelname)s %(name)s %(module)s %(lineno)d - %(message)s"},
        "simple": {"format": "%(levelname)s %(message)s"},
    },
    "handlers": {
        "console": {"level": "DEBUG", "class": "logging.StreamHandler", "formatter": "verbose"},
        "file_daily": {
            "level": "DEBUG",
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": "./django.log",
            "when": "D",
            "interval": 1,
            "backupCount": 7,
            "formatter": "verbose",
        },
    },
    "loggers": {
        "django": {"handlers": ["file_daily", "console"], "level": "DEBUG", "propagate": True},
        "django.request": {"handlers": ["file_daily", "console"], "level": "INFO", "propagate": True},
        "back_end": {"handlers": ["file_daily", "console"], "level": "DEBUG", "propagate": True},
        "": {"handlers": ["file_daily", "console"], "level": "DEBUG", "propagate": True},
    },
}
