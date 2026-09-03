"""
Project-level API views — the browsable index and the health probe.

Individual apps mount their own routers flat under /api/, so this module owns
the single API root rather than letting each router publish a competing one.
"""

from django.db import connection
from django.urls import reverse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

ENDPOINT_GROUPS = {
    'site': ['api-settings', 'api-navigation', 'api-about', 'api-founder'],
    'events': ['api-featured-events'],
    'speakers': ['api-featured-speakers'],
    'team': ['api-team'],
    'gallery': ['api-gallery'],
    'blog': ['api-blog'],
    'sponsors': ['api-sponsors'],
    'forms': [
        'api-contact',
        'api-newsletter',
        'api-newsletter-unsubscribe',
        'api-apply-options',
        'api-apply-speaker',
        'api-apply-volunteer',
        'api-apply-partner',
    ],
}

COLLECTION_ROUTES = [
    'website-settings', 'hero', 'navigation-items', 'social-links', 'faqs',
    'about-sections', 'core-values', 'messages',
    'venues', 'events', 'event-schedule-items',
    'speakers',
    'departments', 'team-members',
    'gallery-albums', 'gallery-images',
    'blog-categories', 'blog-tags', 'blog-posts',
    'sponsor-tiers', 'sponsor-list',
    'contact-messages', 'newsletter-subscribers',
    'speaker-applications', 'volunteer-applications', 'partner-applications',
]


@api_view(['GET'])
@permission_classes([AllowAny])
def api_root_view(request):
    """GET /api/ — a map of every public endpoint."""
    def absolute(path):
        return request.build_absolute_uri(path)

    groups = {
        group: {
            name.removeprefix('api-'): absolute(reverse(name))
            for name in names
        }
        for group, names in ENDPOINT_GROUPS.items()
    }
    groups['collections'] = {
        route: absolute(f'/api/{route}/') for route in COLLECTION_ROUTES
    }

    return Response({
        'service': 'TEDxUMT Lahore API',
        'version': '1.0',
        'health': absolute(reverse('api-health')),
        'admin': absolute('/admin/'),
        'endpoints': groups,
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def health_view(request):
    """GET /api/health/ — liveness probe that also checks the database."""
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
        database_ok = True
    except Exception:  # noqa: BLE001 — the probe must never raise
        database_ok = False

    return Response(
        {'status': 'ok' if database_ok else 'degraded', 'database': database_ok},
        status=200 if database_ok else 503,
    )
