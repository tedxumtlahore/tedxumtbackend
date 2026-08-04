from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import AboutSection, CoreValue, Message
from .serializers import AboutSectionSerializer, CoreValueSerializer, MessageSerializer


@api_view(['GET'])
def about_view(request):
    """GET /api/about/ — all visible about sections, values, and messages combined."""
    sections = AboutSection.objects.filter(is_visible=True)
    values = CoreValue.objects.all()
    messages = Message.objects.filter(is_visible=True)

    return Response({
        'sections': AboutSectionSerializer(sections, many=True, context={'request': request}).data,
        'values': CoreValueSerializer(values, many=True).data,
        'messages': MessageSerializer(messages, many=True, context={'request': request}).data,
    })
