"""
Events views - compatibility endpoints and lightweight public helpers.
"""

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
