from django.db.models import Count, Q
from rest_framework import viewsets

from apps.common.mixins import ActiveQuerysetMixin, SerializerContextMixin
from apps.common.models import StatusChoices
from apps.common.pagination import DefaultPagination
from apps.common.permissions import IsStaffOrReadOnly

from .models import BlogPost, Category, Tag
from .serializers import (
    BlogPostDetailSerializer,
    BlogPostListSerializer,
    BlogPostWriteSerializer,
    CategorySerializer,
    TagSerializer,
)


class CategoryViewSet(SerializerContextMixin, ActiveQuerysetMixin, viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsStaffOrReadOnly]
    pagination_class = DefaultPagination
    lookup_field = 'slug'
    search_fields = ['name', 'description']
    ordering_fields = ['order', 'name']

    def get_queryset(self):
        # annotate() drops Meta.ordering once a GROUP BY is involved, and an
        # unordered queryset makes pagination non-deterministic.
        return super().get_queryset().annotate(
            published_post_count=Count(
                'posts',
                filter=Q(posts__status=StatusChoices.PUBLISHED, posts__is_active=True),
                distinct=True,
            )
        ).order_by('order', 'name')


class TagViewSet(SerializerContextMixin, ActiveQuerysetMixin, viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [IsStaffOrReadOnly]
    pagination_class = DefaultPagination
    lookup_field = 'slug'
    search_fields = ['name']
    ordering_fields = ['name']


class BlogPostViewSet(SerializerContextMixin, ActiveQuerysetMixin, viewsets.ModelViewSet):
    queryset = BlogPost.objects.select_related('category').prefetch_related('tags')
    serializer_class = BlogPostListSerializer
    permission_classes = [IsStaffOrReadOnly]
    pagination_class = DefaultPagination
    lookup_field = 'slug'
    search_fields = ['title', 'excerpt', 'content', 'author_name', 'category__name', 'tags__name']
    ordering_fields = ['published_at', 'created_at', 'title']

    def get_queryset(self):
        queryset = super().get_queryset()

        # Drafts stay invisible to the public; staff can preview them.
        user = getattr(self.request, 'user', None)
        if not (user and user.is_staff):
            queryset = queryset.filter(status=StatusChoices.PUBLISHED)

        params = self.request.query_params
        category = params.get('category')
        if category:
            queryset = queryset.filter(category__slug=category)
        tag = params.get('tag')
        if tag:
            queryset = queryset.filter(tags__slug=tag)
        if params.get('featured') in {'1', 'true', 'True'}:
            queryset = queryset.filter(is_featured=True)

        return queryset.distinct()

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return BlogPostDetailSerializer
        if self.action in {'create', 'update', 'partial_update'}:
            return BlogPostWriteSerializer
        return BlogPostListSerializer
