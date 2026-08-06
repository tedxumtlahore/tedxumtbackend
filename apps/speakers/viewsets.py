from rest_framework import viewsets

from .models import Speaker
from .serializers import SpeakerListSerializer, SpeakerDetailSerializer, SpeakerWriteSerializer


class SpeakerViewSet(viewsets.ModelViewSet):
    queryset = Speaker.objects.select_related('event').all()
    lookup_field = 'slug'

    def get_queryset(self):
        return self.queryset.filter(is_active=True).select_related('event')

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return SpeakerDetailSerializer
        if self.action in {'create', 'update', 'partial_update'}:
            return SpeakerWriteSerializer
        return SpeakerListSerializer
