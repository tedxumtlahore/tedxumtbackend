"""Production settings."""
from .base import *  # noqa: F401, F403
from .base import env  # noqa: F401

DEBUG = False

# ── Security headers ───────────────────────────────────────────────────────
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = False  # the SPA reads this token to send it back

# Behind a TLS-terminating proxy (nginx, Heroku, Railway, ...).
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# ── Static files ───────────────────────────────────────────────────────────
# WhiteNoise lets gunicorn serve the admin's CSS without a separate web server.
# Media is NOT WhiteNoise's job — uploads go to Supabase Storage, configured in
# base.py so that development can exercise the same path.
try:
    import whitenoise  # noqa: F401
except ImportError:
    pass
else:
    MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')  # noqa: F405
    STORAGES['staticfiles'] = {  # noqa: F405
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    }

# Without MEDIA_BUCKET this deploy is writing uploads to a disk that the next
# deploy will erase — and, because Django does not serve MEDIA_URL when DEBUG
# is False, every one of those URLs is already a 404. Say so loudly at startup
# rather than letting the gallery quietly empty itself.
if not MEDIA_BUCKET:  # noqa: F405
    import warnings

    warnings.warn(
        'MEDIA_BUCKET is not set: uploads are going to the local filesystem, '
        'which is ephemeral in production and is not served when DEBUG=False. '
        'Configure Supabase Storage — see .env.example.',
        RuntimeWarning,
        stacklevel=2,
    )

# ── Email ──────────────────────────────────────────────────────────────────
EMAIL_BACKEND = env('EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = env('EMAIL_HOST', default='')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='TEDxUMT Lahore <noreply@tedxumt.pk>')
ADMINS = [('TEDxUMT Organizers', env('ADMIN_EMAIL', default='tedxumtlahore@umt.edu.pk'))]

# ── Logging ────────────────────────────────────────────────────────────────
# Errors go to the rotating file AND to the organizers' inbox.
LOGGING['handlers']['mail_admins'] = {  # noqa: F405
    'class': 'django.utils.log.AdminEmailHandler',
    'level': 'ERROR',
}
LOGGING['loggers']['django.request']['handlers'] = ['console', 'file', 'mail_admins']  # noqa: F405
LOGGING['root']['level'] = 'INFO'  # noqa: F405

# The browsable API is a development convenience — production serves JSON only.
REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'] = [  # noqa: F405
    'rest_framework.renderers.JSONRenderer',
]
