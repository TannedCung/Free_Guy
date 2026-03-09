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

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0', '*']

# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

_database_url = os.environ.get('DATABASE_URL')
if _database_url:
    DATABASES = {'default': dj_database_url.parse(_database_url)}
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),  # noqa: F405
        }
    }

# Cookie security — disable HTTPS enforcement in local dev
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Verbose logging for development
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(asctime)s %(levelname)s %(name)s %(module)s %(lineno)d - %(message)s'
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },
        'file_daily': {
            'level': 'DEBUG',
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': './django.log',
            'when': 'D',
            'interval': 1,
            'backupCount': 7,
            'formatter': 'verbose'
        }
    },
    'loggers': {
        'django': {
            'handlers': ['file_daily', 'console'],
            'level': 'DEBUG',
            'propagate': True
        },
        'django.request': {
            'handlers': ['file_daily', 'console'],
            'level': 'INFO',
            'propagate': True
        },
        'back_end': {
            'handlers': ['file_daily', 'console'],
            'level': 'DEBUG',
            'propagate': True
        },
        '': {
            'handlers': ['file_daily', 'console'],
            'level': 'DEBUG',
            'propagate': True
        },
    }
}
