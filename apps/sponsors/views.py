"""Sponsors views - grouped payload for the public Sponsors page."""

from django.db.models import Prefetch
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import Sponsor, SponsorTier
from .serializers import SponsorTierDetailSerializer


@api_view(['GET'])
@permission_classes([AllowAny])
def sponsors_view(request):
    """GET /api/sponsors/ — visible tiers, ranked, with their sponsors nested."""
    sponsors = Sponsor.objects.filter(is_active=True, is_visible=True).select_related('tier', 'event')
    tiers = (
        SponsorTier.objects.filter(is_active=True, is_visible=True)
        .prefetch_related(Prefetch('sponsors', queryset=sponsors))
    )
    serializer = SponsorTierDetailSerializer(tiers, many=True, context={'request': request})
    return Response({'tiers': serializer.data})
