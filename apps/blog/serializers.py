"""Blog serializers - categories, tags, list/detail/write post serializers."""

from rest_framework import serializers

from apps.common.utils import get_file_url

from .models import BlogPost, Category, Tag


class CategorySerializer(serializers.ModelSerializer):
    post_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            'id', 'name', 'slug', 'description', 'order', 'post_count',
            'created_at', 'updated_at', 'is_active',
        ]
        read_only_fields = ['id', 'slug', 'created_at', 'updated_at']

    def get_post_count(self, obj):
        annotated = getattr(obj, 'published_post_count', None)
        if annotated is not None:
            return annotated
        if not obj.pk:
            return 0
        return obj.posts.filter(status='published', is_active=True).count()


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name', 'slug', 'created_at', 'updated_at', 'is_active']
        read_only_fields = ['id', 'slug', 'created_at', 'updated_at']


class BlogPostListSerializer(serializers.ModelSerializer):
    cover_image = serializers.SerializerMethodField()
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_slug = serializers.CharField(source='category.slug', read_only=True)
    tags = TagSerializer(many=True, read_only=True)

    class Meta:
        model = BlogPost
        fields = [
            'id', 'title', 'slug', 'excerpt', 'cover_image', 'category', 'category_name',
            'category_slug', 'tags', 'author_name', 'status', 'published_at', 'is_featured',
            'reading_minutes', 'created_at', 'updated_at', 'is_active',
        ]

    def get_cover_image(self, obj):
        return get_file_url(self.context.get('request'), obj.cover_image)


class BlogPostDetailSerializer(BlogPostListSerializer):
    related_posts = serializers.SerializerMethodField()

    class Meta(BlogPostListSerializer.Meta):
        fields = BlogPostListSerializer.Meta.fields + ['content', 'related_posts']

    def get_related_posts(self, obj):
        if not obj.pk:
            return []
        siblings = (
            BlogPost.objects
            .filter(status='published', is_active=True, category=obj.category)
            .exclude(pk=obj.pk)
            .select_related('category')
            .prefetch_related('tags')[:3]
        )
        return BlogPostListSerializer(siblings, many=True, context=self.context).data


class BlogPostWriteSerializer(serializers.ModelSerializer):
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True, required=False
    )

    class Meta:
        model = BlogPost
        fields = [
            'id', 'title', 'slug', 'excerpt', 'content', 'category', 'tags', 'cover_image',
            'author_name', 'status', 'published_at', 'is_featured', 'reading_minutes',
            'created_at', 'updated_at', 'is_active',
        ]
        read_only_fields = ['id', 'slug', 'created_at', 'updated_at']
