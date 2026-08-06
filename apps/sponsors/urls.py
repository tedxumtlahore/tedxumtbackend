from django.urls import include, path
from rest_framework.routers import SimpleRouter

from . import views
from .viewsets import SponsorTierViewSet, SponsorViewSet

router = SimpleRouter()
router.register('sponsor-tiers', SponsorTierViewSet, basename='sponsor-tier')
router.register('sponsor-list', SponsorViewSet, basename='sponsor')

urlpatterns = [
    path('sponsors/', views.sponsors_view, name='api-sponsors'),
    path('', include(router.urls)),
]
