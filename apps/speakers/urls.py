from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views
from .viewsets import SpeakerViewSet

router = DefaultRouter()
router.register('speakers', SpeakerViewSet, basename='speaker')

urlpatterns = [
    path('speakers/featured/', views.featured_speakers_view, name='api-featured-speakers'),
    path('', include(router.urls)),
]
