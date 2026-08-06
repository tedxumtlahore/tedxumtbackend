"""
Website views - combined About page payload and CRUD-friendly APIs.
"""

from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import AboutSection, CoreValue, Message
from .serializers import AboutSectionSerializer, CoreValueSerializer, MessageSerializer


class VisibleModelViewSet(viewsets.ReadOnlyModelViewSet):
    def get_queryset(self):
        queryset = self.queryset
        if hasattr(queryset.model, 'is_visible'):
            return queryset.filter(is_visible=True)
        return queryset


class AboutSectionViewSet(VisibleModelViewSet):
    queryset = AboutSection.objects.all()
    serializer_class = AboutSectionSerializer


class CoreValueViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CoreValue.objects.all()
    serializer_class = CoreValueSerializer


class MessageViewSet(VisibleModelViewSet):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer


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
