"""
Central API router — every /api/ endpoint is assembled here.

Each app owns its own `urls.py`; this module only decides mounting order.
Apps are mounted flat under /api/ (no per-app prefix) because the public
resource names are already globally unique.
"""

from django.urls import include, path

from . import views

urlpatterns = [
    path('', views.api_root_view, name='api-root'),
    path('health/', views.health_view, name='api-health'),

    path('', include('apps.common.urls')),
    path('', include('apps.core.urls')),
    path('', include('apps.website.urls')),
    path('', include('apps.events.urls')),
    path('', include('apps.speakers.urls')),
    path('', include('apps.team.urls')),
    path('', include('apps.gallery.urls')),
    path('', include('apps.blog.urls')),
    path('', include('apps.sponsors.urls')),
    path('', include('apps.applications.urls')),
]
