"""Gallery views - flat media feed for the public Gallery page."""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.common.utils import text_choices_to_dicts

from .models import GalleryImage
from .serializers import GalleryImageSerializer


@api_view(['GET'])
@permission_classes([AllowAny])
def gallery_feed_view(request):
    """
    GET /api/gallery/ — flat, filterable media feed.

    Optional query params: ?media_type=photo|video|bts, ?album=<slug>, ?limit=<n>
    """
    images = (
        GalleryImage.objects
        .filter(is_active=True, is_visible=True, album__is_active=True, album__is_visible=True)
        .select_related('album', 'album__event')
    )

    media_type = request.query_params.get('media_type')
    if media_type and media_type != 'all':
        images = images.filter(media_type=media_type)

    album = request.query_params.get('album')
    if album:
        images = images.filter(album__slug=album)

    limit = request.query_params.get('limit')
    if limit and limit.isdigit():
        images = images[: int(limit)]

    return Response({
        'media_types': text_choices_to_dicts(GalleryImage.MediaTypeChoices),
        'results': GalleryImageSerializer(images, many=True, context={'request': request}).data,
    })
