from rest_framework import viewsets

from apps.common.mixins import ActiveQuerysetMixin, SerializerContextMixin
from apps.common.pagination import DefaultPagination
from apps.common.permissions import IsStaffOrReadOnly

from .models import Speaker
from .serializers import SpeakerDetailSerializer, SpeakerListSerializer, SpeakerWriteSerializer


class SpeakerViewSet(SerializerContextMixin, ActiveQuerysetMixin, viewsets.ModelViewSet):
    queryset = Speaker.objects.select_related('event')
    serializer_class = SpeakerListSerializer
    permission_classes = [IsStaffOrReadOnly]
    pagination_class = DefaultPagination
    lookup_field = 'slug'
    filterset_fields = ['featured']
    search_fields = ['name', 'designation', 'organization', 'talk_title', 'bio', 'event__title']
    ordering_fields = ['name', 'created_at']

    def get_queryset(self):
        queryset = super().get_queryset()
        event = self.request.query_params.get('event')
        if event:
            queryset = queryset.filter(event__slug=event)
        return queryset

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return SpeakerDetailSerializer
        if self.action in {'create', 'update', 'partial_update'}:
            return SpeakerWriteSerializer
        return SpeakerListSerializer
