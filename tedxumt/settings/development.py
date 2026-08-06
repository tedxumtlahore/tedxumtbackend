"""Development settings."""
from .base import *  # noqa: F401, F403

DEBUG = True

# Never lock a developer out of their own API while clicking around.
REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {  # noqa: F405
    'anon': '10000/hour',
    'user': '10000/hour',
    'submission': '60/hour',
    'newsletter': '60/hour',
}

# Emails print to the console instead of needing an SMTP server.
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = 'TEDxUMT Lahore <dev@localhost>'

# Set 'django.db.backends' to DEBUG to see every SQL query.
LOGGING['loggers']['django.db.backends'] = {  # noqa: F405
    'handlers': ['console'],
    'level': 'WARNING',
    'propagate': False,
}
