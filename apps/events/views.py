"""
Events views - compatibility endpoints and lightweight public helpers.
"""

from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import Event
from .serializers import EventListSerializer


@api_view(['GET'])
@permission_classes([AllowAny])
def featured_events_view(request):
    """GET /api/events/featured/ — events flagged for the homepage."""
    featured_events = (
        Event.objects
        .filter(is_active=True, is_featured=True)
        .exclude(status=Event.StatusChoices.DRAFT)
        .select_related('venue')
    )
    serializer = EventListSerializer(featured_events, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def next_event_view(request):
    """
    GET /api/events/next/ — what the homepage should feature.

    Three possible states:

    - `published`   an announced upcoming event, serialized in full
    - `coming_soon` an event is being prepared but is still a draft
    - `none`        nothing on the horizon

    In the `coming_soon` state the event's details are deliberately **not**
    sent. The homepage blurs that card, but blur is a CSS filter — the values
    would still be readable in the network response or by disabling one rule.
    Withholding them here is what actually keeps an unannounced event private.

    Note the asymmetry on dates: a published event only counts while it is
    still in the future, but *any* active draft triggers the teaser regardless
    of its date. A draft's date is provisional — organizers routinely leave a
    placeholder on it precisely because the real date isn't settled, and
    gating on that would hide the teaser exactly when it is wanted. The
    trade-off is that an abandoned draft keeps "Coming Soon" on the homepage;
    clear it by deleting the draft or unticking `is_active`.
    """
    live = Event.objects.filter(is_active=True).exclude(status=Event.StatusChoices.CANCELLED)

    announced = (
        live.exclude(status=Event.StatusChoices.DRAFT)
        .filter(start_datetime__gte=timezone.now())
        .select_related('venue')
        .order_by('start_datetime')
        .first()
    )
    if announced is not None:
        return Response({
            'state': 'published',
            'event': EventListSerializer(announced, context={'request': request}).data,
        })

    if live.filter(status=Event.StatusChoices.DRAFT).exists():
        return Response({'state': 'coming_soon', 'event': None})

    return Response({'state': 'none', 'event': None})
