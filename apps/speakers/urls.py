from django.urls import include, path
from rest_framework.routers import SimpleRouter

from . import views
from .viewsets import SpeakerViewSet

router = SimpleRouter()
router.register('speakers', SpeakerViewSet, basename='speaker')

urlpatterns = [
    path('speakers/featured/', views.featured_speakers_view, name='api-featured-speakers'),
    path('', include(router.urls)),
]
