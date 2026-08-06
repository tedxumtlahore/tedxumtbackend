"""
Events views - compatibility endpoints and lightweight public helpers.
"""

from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Event
from .serializers import EventListSerializer


@api_view(['GET'])
def featured_events_view(request):
    featured_events = Event.objects.select_related('venue').filter(is_active=True, is_featured=True)
    serializer = EventListSerializer(featured_events, many=True, context={'request': request})
    return Response(serializer.data)
