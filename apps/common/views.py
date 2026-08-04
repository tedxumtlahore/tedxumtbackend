from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import StatusChoices
from .serializers import ChoiceOptionSerializer
from .utils import text_choices_to_dicts


@api_view(['GET'])
def health_view(request):
    return Response({'status': 'ok', 'service': 'common'})


@api_view(['GET'])
def status_choices_view(request):
    serializer = ChoiceOptionSerializer(text_choices_to_dicts(StatusChoices), many=True)
    return Response(serializer.data)
