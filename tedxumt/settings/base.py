"""
TEDxUMT Backend — Base Settings
Shared by all environments.
"""

from datetime import timedelta
from pathlib import Path

import environ

# ── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # tedxumt_backend/

# ── Environment ────────────────────────────────────────────────────────────
env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ['localhost', '127.0.0.1', "tedxumtbackend.onrender.com"]),
)
environ.Env.read_env(BASE_DIR / '.env')

# ── Security ───────────────────────────────────────────────────────────────
SECRET_KEY = env('SECRET_KEY')
DEBUG = env('DEBUG')
ALLOWED_HOSTS = env('ALLOWED_HOSTS')

# ── Application Definition ─────────────────────────────────────────────────
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    # Lets a volunteer's token be revoked when they leave the team — a plain
    # JWT stays valid until it expires, which is not good enough for door access.
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'django_filters',
    'django_extensions',
]

LOCAL_APPS = [
    'apps.common',
    'apps.accounts',
    'apps.core',
    'apps.website',
    'apps.events',
    'apps.speakers',
    'apps.team',
    'apps.gallery',
    'apps.blog',
    'apps.sponsors',
    'apps.applications',
    'apps.ticketing',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ── Middleware ─────────────────────────────────────────────────────────────
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',            # must be first
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'tedxumt.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'tedxumt.wsgi.application'

# ── Database ───────────────────────────────────────────────────────────────
DATABASES = {
    'default': env.db('DATABASE_URL', default='sqlite:///db.sqlite3')
}

# A relative sqlite path resolves against the current working directory, which
# silently creates a second, empty database when the server is started from
# anywhere but the project root. Anchor it to BASE_DIR instead.
_default_db = DATABASES['default']
if 'sqlite' in _default_db.get('ENGINE', '') and not Path(_default_db['NAME']).is_absolute():
    _default_db['NAME'] = str(BASE_DIR / _default_db['NAME'])

# ── Password Validation ────────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ── Internationalization ───────────────────────────────────────────────────
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Karachi'
USE_I18N = True
USE_TZ = True

# ── Static Files ───────────────────────────────────────────────────────────
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static'] if (BASE_DIR / 'static').exists() else []

# ── Media Files ────────────────────────────────────────────────────────────
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / env('MEDIA_ROOT', default='media')

# Reject uploads larger than 10 MB outright.
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

# ── Default Primary Key ────────────────────────────────────────────────────
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── Django REST Framework ──────────────────────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.MultiPartParser',
        'rest_framework.parsers.FormParser',
    ],
    # Public content is world-readable; writes require a staff session.
    # Individual viewsets tighten this further (see apps/common/permissions.py).
    'DEFAULT_PERMISSION_CLASSES': [
        'apps.common.permissions.IsStaffOrReadOnly',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        # Session auth drives the admin-backed CMS. JWT is for the volunteer
        # check-in scanner, which runs on a phone and has no session cookie.
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '1000/hour',
        'user': '5000/hour',
        'submission': '10/hour',     # contact + application form POSTs
        'newsletter': '20/hour',
        'registration': '15/hour',   # event registration holds a seat, so cap it
        'account': '10/hour',        # attendee signup — cheap to send, permanent for us
        'checkin': '2000/hour',      # a volunteer scans continuously on event day
    },
    'DEFAULT_PAGINATION_CLASS': 'apps.common.pagination.DefaultPagination',
    'PAGE_SIZE': 20,
    'EXCEPTION_HANDLER': 'apps.common.exceptions.api_exception_handler',
}

# ── JWT (volunteer check-in scanner) ───────────────────────────────────────
# Short access tokens because the scanner holds them in browser storage, where
# an XSS bug would expose them. Rotation plus the blacklist means a stolen or
# revoked credential stops working quickly rather than at its natural expiry.
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(hours=12),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
}

# ── Ticketing ──────────────────────────────────────────────────────────────
# Where a ticket's QR and "view your ticket" links point. Emails are sent
# without a request to build absolute URLs from (admin actions, management
# commands), so the public site's address has to be configured explicitly.
TICKET_BASE_URL = env('TICKET_BASE_URL', default='http://localhost:5173')

# Ticket delivery is through the attendee's account on the website, not email.
# No SMTP is connected, so attempting to send would log an exception on every
# confirmation for no benefit. Flip this to True once a mail provider exists;
# `send_ticket_email` is unchanged and still wired to the admin resend action.
TICKET_EMAIL_ENABLED = env.bool('TICKET_EMAIL_ENABLED', default=False)

# ── CORS ───────────────────────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS = env.list(
    'CORS_ALLOWED_ORIGINS',
    default=['http://localhost:5173', 'http://127.0.0.1:5173', 'https://tedxumtbackend.onrender.com'],
)
CORS_ALLOW_CREDENTIALS = False

# The admin posts forms from its own origin, but a separately hosted frontend
# needs to be trusted for any session-authenticated write.
CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS', default=CORS_ALLOWED_ORIGINS)

# ── Logging ────────────────────────────────────────────────────────────────
LOG_DIR = BASE_DIR / 'logs'
LOG_DIR.mkdir(exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {name} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOG_DIR / 'tedxumt.log',
            'maxBytes': 5 * 1024 * 1024,
            'backupCount': 3,
            'formatter': 'verbose',
            'encoding': 'utf-8',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console', 'file'],
            'level': 'ERROR',
            'propagate': False,
        },
        'apps': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
