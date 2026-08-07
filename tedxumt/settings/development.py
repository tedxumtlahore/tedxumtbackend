"""Development settings."""
from .base import *  # noqa: F401, F403

DEBUG = True

# Never lock a developer out of their own API while clicking around.
# Merged into the base rates rather than replacing them: replacing the dict
# drops any scope added in base.py that isn't repeated here, and a missing
# scope is not a lenient limit — it raises ImproperlyConfigured at request time.
REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {  # noqa: F405
    **REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'],  # noqa: F405
    'anon': '10000/hour',
    'user': '10000/hour',
    'submission': '60/hour',
    'newsletter': '60/hour',
    'registration': '200/hour',
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
