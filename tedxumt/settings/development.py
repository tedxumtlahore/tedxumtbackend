"""Development settings."""
from .base import *  # noqa: F401, F403

DEBUG = True

# Show SQL queries in shell
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {'class': 'logging.StreamHandler'},
    },
    'loggers': {
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'WARNING',  # set to DEBUG to see all SQL
        },
    },
}
