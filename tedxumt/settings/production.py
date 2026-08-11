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
try:
    import whitenoise  # noqa: F401
except ImportError:
    _STATIC_BACKEND = 'django.contrib.staticfiles.storage.StaticFilesStorage'
else:
    MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')  # noqa: F405
    _STATIC_BACKEND = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ── Media files (object storage) ───────────────────────────────────────────
# Render, Heroku and friends have an ephemeral filesystem: every deploy throws
# away whatever was written to disk. That would silently destroy the gallery
# and — worse — the payment screenshots that are the evidence trail for who
# actually paid. Uploads therefore go to S3-compatible object storage.
#
# Two buckets, because the two kinds of upload have opposite exposure needs.
# See apps/common/storages.py. Setting MEDIA_BUCKET switches this on; without
# it the settings fall back to local disk, which is correct for a single-box
# deployment with a real persistent volume.
MEDIA_BUCKET = env('MEDIA_BUCKET', default='')

if MEDIA_BUCKET:
    _S3_BASE = {
        'access_key': env('S3_ACCESS_KEY_ID'),
        'secret_key': env('S3_SECRET_ACCESS_KEY'),
        'endpoint_url': env('S3_ENDPOINT_URL'),
        'region_name': env('S3_REGION', default='us-east-1'),
        # Supabase (and most S3-compatible services that are not AWS) serve
        # buckets as a path, not as a subdomain of the endpoint.
        'addressing_style': 'path',
        # Object ACLs are an AWS concept; Supabase Storage rejects them.
        # Public vs private is a property of the bucket itself there.
        'default_acl': None,
        # Never let a second upload silently replace the first.
        'file_overwrite': False,
    }

    STORAGES = {
        # Public bucket: gallery, portraits, logos, blog covers. These are
        # meant to be seen, so URLs are unsigned and therefore cacheable.
        'default': {
            'BACKEND': 'storages.backends.s3boto3.S3Boto3Storage',
            'OPTIONS': {**_S3_BASE, 'bucket_name': MEDIA_BUCKET, 'querystring_auth': False},
        },
        # Private bucket: payment proofs only. URLs are signed and expire, so a
        # leaked link stops working — these screenshots show the sender's
        # balance and transaction history.
        'private': {
            'BACKEND': 'storages.backends.s3boto3.S3Boto3Storage',
            'OPTIONS': {
                **_S3_BASE,
                'bucket_name': env('PRIVATE_MEDIA_BUCKET', default=f'{MEDIA_BUCKET}-private'),
                'querystring_auth': True,
                'querystring_expire': env.int('PRIVATE_URL_EXPIRY', default=600),
            },
        },
        'staticfiles': {'BACKEND': _STATIC_BACKEND},
    }
else:
    STORAGES = {
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': _STATIC_BACKEND},
    }

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
