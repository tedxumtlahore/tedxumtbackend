"""Blog views - combined index payload for the public Blog page."""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.common.models import StatusChoices

from .models import BlogPost, Category
from .serializers import BlogPostListSerializer, CategorySerializer


@api_view(['GET'])
@permission_classes([AllowAny])
def blog_index_view(request):
    """GET /api/blog/ — the featured post plus the rest, in one round trip."""
    published = (
        BlogPost.objects
        .filter(is_active=True, status=StatusChoices.PUBLISHED)
        .select_related('category')
        .prefetch_related('tags')
    )

    featured = published.filter(is_featured=True).first()
    rest = published.exclude(pk=featured.pk) if featured else published

    context = {'request': request}
    return Response({
        'featured': BlogPostListSerializer(featured, context=context).data if featured else None,
        'posts': BlogPostListSerializer(rest, many=True, context=context).data,
        'categories': CategorySerializer(
            Category.objects.filter(is_active=True), many=True, context=context
        ).data,
    })
