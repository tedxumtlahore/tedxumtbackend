from django.db.models import Count, Prefetch, Q
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

    def get_queryset(self):
        schedule_items = EventScheduleItem.objects.select_related('speaker')
        return (
            self.queryset
            .filter(is_active=True)
            .select_related('venue')
            .prefetch_related(Prefetch('schedule_items', queryset=schedule_items))
            .annotate(speaker_count=Count('schedule_items', filter=Q(schedule_items__speaker__isnull=False), distinct=True))
        )

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return EventDetailSerializer
        if self.action in {'create', 'update', 'partial_update'}:
            return EventWriteSerializer
        return EventListSerializer


class EventScheduleItemViewSet(ActiveQuerysetMixin, viewsets.ModelViewSet):
    queryset = EventScheduleItem.objects.select_related('event', 'speaker').all()
    serializer_class = EventScheduleItemSerializer
