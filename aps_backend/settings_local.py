# Local preview settings: inherit everything from the real settings, but run on
# SQLite so the site/CMS can be viewed without a MySQL/MariaDB server.
# Run with:  DJANGO_SETTINGS_MODULE=aps_backend.settings_local
from .settings import *  # noqa: F401,F403
from .settings import BASE_DIR

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
