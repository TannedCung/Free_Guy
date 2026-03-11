"""
Django production settings for frontend_server project.

Imports base settings and adds production-specific configuration:
  - DEBUG = False
  - ALLOWED_HOSTS from DJANGO_ALLOWED_HOSTS env var (required)
  - PostgreSQL via DATABASE_URL env var (required)
  - whitenoise for static file serving
  - Enforced HTTPS cookies and security headers

Usage: DJANGO_ENV=production
"""

import os

import dj_database_url

from .base import *  # noqa: F401, F403

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

_allowed_hosts_env = os.environ.get("DJANGO_ALLOWED_HOSTS", "")
ALLOWED_HOSTS = [h.strip() for h in _allowed_hosts_env.split(",") if h.strip()]
if not ALLOWED_HOSTS:
    raise ValueError(
        "DJANGO_ALLOWED_HOSTS environment variable is required in production. "
        "Set it to a comma-separated list of allowed hostnames."
    )

# Database — PostgreSQL required in production
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

_database_url = os.environ.get("DATABASE_URL")
if not _database_url:
    raise ValueError(
        "DATABASE_URL environment variable is required in production. "
        "Example: postgres://user:password@localhost:5432/free_guy_db"
    )
DATABASES = {"default": dj_database_url.parse(_database_url)}

# Cookie security — enforce HTTPS in production
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# whitenoise for serving compressed static files in production
# https://whitenoise.readthedocs.io/en/stable/django.html
INSTALLED_APPS = ["whitenoise.runserver_nostatic"] + INSTALLED_APPS  # noqa: F405

MIDDLEWARE = [  # noqa: F405
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # must be right after SecurityMiddleware
] + [m for m in MIDDLEWARE if m != "django.middleware.security.SecurityMiddleware"]  # noqa: F405

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# Serve the React SPA static bundle (assets/, vite.svg, etc.) at root URL paths.
# Whitenoise resolves /assets/... directly from this directory before Django routing.
WHITENOISE_ROOT = REACT_DIST_DIR  # noqa: F405

# Production logging — WARNING level only to reduce noise
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "%(asctime)s %(levelname)s %(name)s %(module)s %(lineno)d - %(message)s"},
    },
    "handlers": {
        "console": {"level": "WARNING", "class": "logging.StreamHandler", "formatter": "verbose"},
    },
    "loggers": {
        "django": {"handlers": ["console"], "level": "WARNING", "propagate": True},
        "django.request": {"handlers": ["console"], "level": "ERROR", "propagate": True},
        "": {"handlers": ["console"], "level": "WARNING", "propagate": True},
    },
}
