from django.urls import include, path
from rest_framework.routers import SimpleRouter

from . import views
from .viewsets import VenueViewSet, EventViewSet, EventScheduleItemViewSet

router = SimpleRouter()
router.register('venues', VenueViewSet, basename='venue')
router.register('events', EventViewSet, basename='event')
router.register('event-schedule-items', EventScheduleItemViewSet, basename='event-schedule-item')

urlpatterns = [
    path('events/featured/', views.featured_events_view, name='api-featured-events'),
    path('', include(router.urls)),
]
