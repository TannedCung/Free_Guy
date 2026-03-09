"""
Settings selector for frontend_server.

Selects the active settings module based on the DJANGO_ENV environment variable:
  - DJANGO_ENV=development  →  settings.development  (default)
  - DJANGO_ENV=production   →  settings.production

DJANGO_SETTINGS_MODULE can still be used to bypass this entirely, e.g.:
  DJANGO_SETTINGS_MODULE=frontend_server.settings.production
"""

import os

_env = os.environ.get('DJANGO_ENV', 'development')

if _env == 'production':
    from .production import *  # noqa: F401, F403
else:
    from .development import *  # noqa: F401, F403
