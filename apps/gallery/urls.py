from django.urls import include, path
from rest_framework.routers import SimpleRouter

from . import views
from .viewsets import GalleryAlbumViewSet, GalleryImageViewSet

router = SimpleRouter()
router.register('gallery-albums', GalleryAlbumViewSet, basename='gallery-album')
router.register('gallery-images', GalleryImageViewSet, basename='gallery-image')

urlpatterns = [
    path('gallery/', views.gallery_feed_view, name='api-gallery'),
    path('', include(router.urls)),
]
