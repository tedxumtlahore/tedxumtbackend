"""
Website views - combined About page payload and CRUD-friendly APIs.
"""

from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.common.mixins import ActiveQuerysetMixin, SerializerContextMixin, VisibleQuerysetMixin
from apps.common.permissions import IsStaffOrReadOnly

from .models import AboutSection, CoreValue, Message
from .serializers import AboutSectionSerializer, CoreValueSerializer, MessageSerializer


class AboutSectionViewSet(SerializerContextMixin, VisibleQuerysetMixin, viewsets.ModelViewSet):
    queryset = AboutSection.objects.all()
    serializer_class = AboutSectionSerializer
    permission_classes = [IsStaffOrReadOnly]
    pagination_class = None
    lookup_field = 'section_key'
    search_fields = ['heading', 'body', 'eyebrow']
    ordering_fields = ['order', 'section_key']


class CoreValueViewSet(SerializerContextMixin, ActiveQuerysetMixin, viewsets.ModelViewSet):
    queryset = CoreValue.objects.all()
    serializer_class = CoreValueSerializer
    permission_classes = [IsStaffOrReadOnly]
    pagination_class = None
    filterset_fields = ['icon_key']
    search_fields = ['title', 'description']
    ordering_fields = ['order', 'title']


class MessageViewSet(SerializerContextMixin, VisibleQuerysetMixin, viewsets.ModelViewSet):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
    permission_classes = [IsStaffOrReadOnly]
    pagination_class = None
    lookup_field = 'message_type'
    filterset_fields = ['message_type']
    search_fields = ['person_name', 'role_title', 'message_body']
    ordering_fields = ['order', 'message_type']


@api_view(['GET'])
@permission_classes([AllowAny])
def about_view(request):
    """GET /api/about/ — all visible about sections, values, and messages combined."""
    context = {'request': request}
    sections = AboutSection.objects.filter(is_active=True, is_visible=True)
    values = CoreValue.objects.filter(is_active=True)
    messages = Message.objects.filter(is_active=True, is_visible=True)

    return Response({
        'sections': AboutSectionSerializer(sections, many=True, context=context).data,
        'values': CoreValueSerializer(values, many=True, context=context).data,
        'messages': MessageSerializer(messages, many=True, context=context).data,
    })
