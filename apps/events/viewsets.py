from rest_framework import viewsets

from .models import Venue, Event, EventScheduleItem
from .serializers import (
    VenueSerializer,
    EventListSerializer,
    EventDetailSerializer,
    EventWriteSerializer,
    EventScheduleItemSerializer,
)


class ActiveQuerysetMixin:
    def get_queryset(self):
        return self.queryset.filter(is_active=True)


class VenueViewSet(ActiveQuerysetMixin, viewsets.ModelViewSet):
    queryset = Venue.objects.all()
    serializer_class = VenueSerializer


class EventViewSet(ActiveQuerysetMixin, viewsets.ModelViewSet):
    queryset = Event.objects.select_related('venue').all()
    serializer_class = EventListSerializer
    lookup_field = 'slug'

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return EventDetailSerializer
        if self.action in {'create', 'update', 'partial_update'}:
            return EventWriteSerializer
        return EventListSerializer


class EventScheduleItemViewSet(ActiveQuerysetMixin, viewsets.ModelViewSet):
    queryset = EventScheduleItem.objects.select_related('event', 'speaker').all()
    serializer_class = EventScheduleItemSerializer
