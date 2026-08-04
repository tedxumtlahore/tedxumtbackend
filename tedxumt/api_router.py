"""
Central API router — all /api/ endpoints assembled here.
"""

from django.urls import path, include

urlpatterns = [
    # Common metadata and health endpoints
    path('', include('apps.common.urls')),

    # Core: settings, navigation, hero, FAQs
    path('', include('apps.core.urls')),

    # Website: about page, messages
    path('', include('apps.website.urls')),

    # Events
    path('', include('apps.events.urls')),

    # Team
    path('', include('apps.team.urls')),

    # Speakers
    path('', include('apps.speakers.urls')),

    # Gallery
    path('', include('apps.gallery.urls')),

    # Blog
    path('', include('apps.blog.urls')),

    # Sponsors
    path('', include('apps.sponsors.urls')),

    # Applications (forms)
    path('', include('apps.applications.urls')),
]
