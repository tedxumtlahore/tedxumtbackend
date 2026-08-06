"""
Speakers views - compatibility helpers for public speaker data.
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import Speaker
from .serializers import SpeakerListSerializer


@api_view(['GET'])
@permission_classes([AllowAny])
def featured_speakers_view(request):
    """GET /api/speakers/featured/ — speakers flagged for the homepage."""
    featured_speakers = Speaker.objects.select_related('event').filter(is_active=True, featured=True)
    serializer = SpeakerListSerializer(featured_speakers, many=True, context={'request': request})
    return Response(serializer.data)
