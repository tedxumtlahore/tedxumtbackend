from django.db.models import Count, Prefetch, Q
from rest_framework import viewsets

from apps.common.mixins import SerializerContextMixin, VisibleQuerysetMixin
from apps.common.pagination import DefaultPagination, LargePagination
from apps.common.permissions import IsStaffOrReadOnly

from .models import GalleryAlbum, GalleryImage
from .serializers import GalleryAlbumDetailSerializer, GalleryAlbumSerializer, GalleryImageSerializer


class GalleryAlbumViewSet(SerializerContextMixin, VisibleQuerysetMixin, viewsets.ModelViewSet):
    queryset = GalleryAlbum.objects.select_related('event')
    serializer_class = GalleryAlbumSerializer
    permission_classes = [IsStaffOrReadOnly]
    pagination_class = DefaultPagination
    lookup_field = 'slug'
    search_fields = ['title', 'description', 'event__title']
    ordering_fields = ['order', 'created_at', 'title']

    def get_queryset(self):
        images = GalleryImage.objects.filter(is_visible=True, is_active=True)
        queryset = (
            super().get_queryset()
            .prefetch_related(Prefetch('images', queryset=images))
            .annotate(
                visible_image_count=Count(
                    'images',
                    filter=Q(images__is_visible=True, images__is_active=True),
                    distinct=True,
                )
            )
            .order_by('order', '-created_at', 'title')
        )
        event = self.request.query_params.get('event')
        if event:
            queryset = queryset.filter(event__slug=event)
        return queryset

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return GalleryAlbumDetailSerializer
        return GalleryAlbumSerializer


class GalleryImageViewSet(SerializerContextMixin, VisibleQuerysetMixin, viewsets.ModelViewSet):
    queryset = GalleryImage.objects.select_related('album', 'album__event')
    serializer_class = GalleryImageSerializer
    permission_classes = [IsStaffOrReadOnly]
    pagination_class = LargePagination
    search_fields = ['caption', 'alt_text', 'album__title']
    ordering_fields = ['order', 'created_at']

    def get_queryset(self):
        queryset = super().get_queryset()
        album = self.request.query_params.get('album')
        if album:
            queryset = queryset.filter(album__slug=album)
        media_type = self.request.query_params.get('media_type')
        if media_type:
            queryset = queryset.filter(media_type=media_type)
        return queryset
