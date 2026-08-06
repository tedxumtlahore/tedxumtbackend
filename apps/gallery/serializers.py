"""Gallery serializers - albums and images."""

from rest_framework import serializers

from apps.common.utils import get_file_url

from .models import GalleryAlbum, GalleryImage


class GalleryImageSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    image_upload = serializers.ImageField(source='image', write_only=True, required=False)
    album_slug = serializers.CharField(source='album.slug', read_only=True)
    resolved_alt_text = serializers.SerializerMethodField()

    class Meta:
        model = GalleryImage
        fields = [
            'id', 'album', 'album_slug', 'image', 'image_upload', 'caption', 'alt_text',
            'resolved_alt_text', 'media_type', 'video_url', 'order', 'is_visible',
            'created_at', 'updated_at', 'is_active',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_image(self, obj):
        return get_file_url(self.context.get('request'), obj.image)

    def get_resolved_alt_text(self, obj):
        return obj.alt_text or obj.caption or f'{obj.album.title} gallery image'

    def validate(self, attrs):
        # `image` is exposed read-only, so DRF cannot enforce the model's
        # requirement on create — do it here against the write-only alias.
        if self.instance is None and not attrs.get('image'):
            raise serializers.ValidationError({'image_upload': 'An image file is required.'})
        if attrs.get('media_type') == GalleryImage.MediaTypeChoices.VIDEO:
            video_url = attrs.get('video_url', getattr(self.instance, 'video_url', ''))
            if not video_url:
                raise serializers.ValidationError({'video_url': 'Video items require a video URL.'})
        return attrs


class GalleryAlbumSerializer(serializers.ModelSerializer):
    cover_image = serializers.SerializerMethodField()
    cover_image_upload = serializers.ImageField(source='cover_image', write_only=True, required=False)
    event_title = serializers.CharField(source='event.title', read_only=True)
    event_slug = serializers.CharField(source='event.slug', read_only=True)
    image_count = serializers.SerializerMethodField()

    class Meta:
        model = GalleryAlbum
        fields = [
            'id', 'title', 'slug', 'description', 'event', 'event_title', 'event_slug',
            'cover_image', 'cover_image_upload', 'image_count', 'order', 'is_visible',
            'created_at', 'updated_at', 'is_active',
        ]
        read_only_fields = ['id', 'slug', 'created_at', 'updated_at']

    def get_cover_image(self, obj):
        return get_file_url(self.context.get('request'), obj.cover_image)

    def get_image_count(self, obj):
        annotated = getattr(obj, 'visible_image_count', None)
        if annotated is not None:
            return annotated
        if not obj.pk:
            return 0
        return obj.images.filter(is_visible=True, is_active=True).count()


class GalleryAlbumDetailSerializer(GalleryAlbumSerializer):
    images = serializers.SerializerMethodField()

    class Meta(GalleryAlbumSerializer.Meta):
        fields = GalleryAlbumSerializer.Meta.fields + ['images']

    def get_images(self, obj):
        if not obj.pk:
            return []
        images = [i for i in obj.images.all() if i.is_visible and i.is_active]
        return GalleryImageSerializer(images, many=True, context=self.context).data
