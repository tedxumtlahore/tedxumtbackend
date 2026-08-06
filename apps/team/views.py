"""Team views - grouped payload for the public Team page."""

from django.db.models import Prefetch
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import Department, TeamMember
from .serializers import DepartmentDetailSerializer


@api_view(['GET'])
@permission_classes([AllowAny])
def team_view(request):
    """GET /api/team/ — visible departments with their visible members nested."""
    members = TeamMember.objects.filter(is_active=True, is_visible=True).select_related('department')
    departments = (
        Department.objects.filter(is_active=True, is_visible=True)
        .prefetch_related(Prefetch('members', queryset=members))
    )
    serializer = DepartmentDetailSerializer(departments, many=True, context={'request': request})
    return Response({'departments': serializer.data})
