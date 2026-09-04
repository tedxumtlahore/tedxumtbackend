from rest_framework import serializers

from apps.common.utils import get_file_url

from .models import AboutSection, CoreValue, Founder, Message


class AboutSectionSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = AboutSection
        fields = [
            'id', 'section_key', 'eyebrow', 'heading', 'body',
            'image', 'image_position', 'external_link_label',
            'external_link_url', 'order', 'is_visible',
            'created_at', 'updated_at', 'is_active',
        ]

    def get_image(self, obj):
        request = self.context.get('request')
        return get_file_url(request, obj.image)


class CoreValueSerializer(serializers.ModelSerializer):
    class Meta:
        model = CoreValue
        fields = ['id', 'icon_key', 'title', 'description', 'order', 'created_at', 'updated_at', 'is_active']


class MessageSerializer(serializers.ModelSerializer):
    photo = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            'id', 'message_type', 'person_name', 'role_title', 'message_body',
            'photo', 'order', 'is_visible', 'created_at', 'updated_at', 'is_active',
        ]

    def get_photo(self, obj):
        request = self.context.get('request')
        return get_file_url(request, obj.photo)


class FounderSerializer(serializers.ModelSerializer):
    photo = serializers.SerializerMethodField()

    class Meta:
        model = Founder
        fields = [
            'id', 'name', 'role_title', 'photo', 'story',
            'email', 'linkedin', 'instagram',
            'is_visible', 'created_at', 'updated_at', 'is_active',
        ]

    def get_photo(self, obj):
        return get_file_url(self.context.get('request'), obj.photo)
