from django.db.models import Count, Prefetch, Q
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common.mixins import ActiveQuerysetMixin, SerializerContextMixin
from apps.common.pagination import DefaultPagination
from apps.common.permissions import IsStaffOrReadOnly
from apps.common.utils import text_choices_to_dicts

from .models import Event, EventScheduleItem, Venue
from .serializers import (
    EventDetailSerializer,
    EventListSerializer,
    EventScheduleItemSerializer,
    EventWriteSerializer,
    VenueSerializer,
)


class VenueViewSet(SerializerContextMixin, ActiveQuerysetMixin, viewsets.ModelViewSet):
    queryset = Venue.objects.all()
    serializer_class = VenueSerializer
    permission_classes = [IsStaffOrReadOnly]
    pagination_class = DefaultPagination
    filterset_fields = ['city']
    search_fields = ['name', 'address', 'city']
    ordering_fields = ['name', 'city', 'created_at']


class EventViewSet(SerializerContextMixin, ActiveQuerysetMixin, viewsets.ModelViewSet):
    queryset = Event.objects.select_related('venue')
    serializer_class = EventListSerializer
    permission_classes = [IsStaffOrReadOnly]
    pagination_class = DefaultPagination
    lookup_field = 'slug'
    filterset_fields = ['event_type', 'status', 'is_featured']
    search_fields = ['title', 'short_description', 'description', 'venue__name', 'venue__city']
    ordering_fields = ['start_datetime', 'title', 'created_at']

    def get_queryset(self):
        schedule_items = EventScheduleItem.objects.filter(is_active=True).select_related('speaker')
        queryset = (
            super().get_queryset()
            .prefetch_related(Prefetch('schedule_items', queryset=schedule_items))
            .annotate(
                # The billed lineup, not the schedule — a speaker can be
                # announced before their slot is assigned.
                speaker_count=Count(
                    'speakers',
                    filter=Q(speakers__is_active=True),
                    distinct=True,
                )
            )
            .order_by('-start_datetime', 'title')
        )

        # Drafts are internal until an organizer marks them upcoming or past.
        user = getattr(self.request, 'user', None)
        if not (user and user.is_staff):
            queryset = queryset.exclude(status=Event.StatusChoices.DRAFT)

        year = self.request.query_params.get('year')
        if year and year.isdigit():
            queryset = queryset.filter(start_datetime__year=int(year))

        return queryset

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return EventDetailSerializer
        if self.action in {'create', 'update', 'partial_update'}:
            return EventWriteSerializer
        return EventListSerializer

    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """GET /api/events/upcoming/ — future events, soonest first."""
        events = self.filter_queryset(self.get_queryset()).filter(
            start_datetime__gte=timezone.now()
        ).order_by('start_datetime')
        serializer = self.get_serializer(events, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def options(self, request):
        """GET /api/events/options/ — choice lists for filter UIs."""
        return Response({
            'event_types': text_choices_to_dicts(Event.EventTypeChoices),
            'statuses': text_choices_to_dicts(Event.StatusChoices),
        })


class EventScheduleItemViewSet(SerializerContextMixin, ActiveQuerysetMixin, viewsets.ModelViewSet):
    queryset = EventScheduleItem.objects.select_related('event', 'speaker')
    serializer_class = EventScheduleItemSerializer
    permission_classes = [IsStaffOrReadOnly]
    pagination_class = DefaultPagination
    search_fields = ['title', 'description', 'event__title', 'speaker__name']
    ordering_fields = ['start_time', 'title']

    def get_queryset(self):
        queryset = super().get_queryset()
        event = self.request.query_params.get('event')
        if event:
            queryset = queryset.filter(event__slug=event)
        return queryset
