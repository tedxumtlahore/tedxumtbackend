from django.db.models import Prefetch
from rest_framework import viewsets

from apps.common.mixins import SerializerContextMixin, VisibleQuerysetMixin
from apps.common.pagination import DefaultPagination
from apps.common.permissions import IsStaffOrReadOnly

from .models import Sponsor, SponsorTier
from .serializers import SponsorSerializer, SponsorTierDetailSerializer, SponsorTierSerializer


class SponsorTierViewSet(SerializerContextMixin, VisibleQuerysetMixin, viewsets.ModelViewSet):
    queryset = SponsorTier.objects.all()
    serializer_class = SponsorTierSerializer
    permission_classes = [IsStaffOrReadOnly]
    pagination_class = DefaultPagination
    lookup_field = 'slug'
    search_fields = ['name', 'description', 'benefits']
    ordering_fields = ['order', 'name']

    def get_queryset(self):
        sponsors = Sponsor.objects.select_related('tier', 'event')
        return super().get_queryset().prefetch_related(Prefetch('sponsors', queryset=sponsors))

    def get_serializer_class(self):
        if self.action in {'list', 'retrieve'}:
            return SponsorTierDetailSerializer
        return SponsorTierSerializer


class SponsorViewSet(SerializerContextMixin, VisibleQuerysetMixin, viewsets.ModelViewSet):
    queryset = Sponsor.objects.select_related('tier', 'event')
    serializer_class = SponsorSerializer
    permission_classes = [IsStaffOrReadOnly]
    pagination_class = DefaultPagination
    lookup_field = 'slug'
    search_fields = ['name', 'description', 'tier__name']
    ordering_fields = ['order', 'name']

    def get_queryset(self):
        queryset = super().get_queryset()
        tier = self.request.query_params.get('tier')
        if tier:
            queryset = queryset.filter(tier__slug=tier)
        event = self.request.query_params.get('event')
        if event:
            queryset = queryset.filter(event__slug=event)
        return queryset
