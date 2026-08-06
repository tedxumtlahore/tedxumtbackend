"""
Applications views.

The submission endpoints all live on viewsets (see viewsets.py); this module
only exposes the choice lists the Apply page needs to render its dropdowns.
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.common.utils import text_choices_to_dicts

from .models import PartnerApplication, VolunteerApplication


@api_view(['GET'])
@permission_classes([AllowAny])
def application_options_view(request):
    """GET /api/apply/options/ — dropdown choices for the application forms."""
    return Response({
        'availability': text_choices_to_dicts(VolunteerApplication.AvailabilityChoices),
        'partnership_types': text_choices_to_dicts(PartnerApplication.PartnershipTypeChoices),
    })
