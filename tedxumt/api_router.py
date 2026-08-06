"""
Central API router - all /api/ endpoints assembled here.
"""

from django.urls import include, path

urlpatterns = [
    path('', include('apps.core.urls')),
    path('', include('apps.website.urls')),
    path('', include('apps.events.urls')),
    path('', include('apps.speakers.urls')),
    path('v1/', include('apps.speakers.urls')),
]
