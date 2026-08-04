"""
TEDxUMT Backend — Root URL Configuration
All API routes are versioned under /api/
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Django Admin (CMS entry point for organizers)
    path('admin/', admin.site.urls),

    # REST API
    path('api/', include('tedxumt.api_router')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Admin customization
admin.site.site_header = 'TEDxUMT Lahore — Admin'
admin.site.site_title = 'TEDxUMT Admin'
admin.site.index_title = 'Content Management'
