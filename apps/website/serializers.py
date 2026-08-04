from rest_framework import serializers
from .models import AboutSection, CoreValue, Message


class AboutSectionSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = AboutSection
        fields = [
            'id', 'section_key', 'eyebrow', 'heading', 'body',
            'image', 'image_position', 'external_link_label',
            'external_link_url', 'order',
        ]

    def get_image(self, obj):
        if obj.image:
            request = self.context.get('request')
            return request.build_absolute_uri(obj.image.url) if request else obj.image.url
        return None


class CoreValueSerializer(serializers.ModelSerializer):
    class Meta:
        model = CoreValue
        fields = ['id', 'icon_key', 'title', 'description', 'order']


class MessageSerializer(serializers.ModelSerializer):
    photo = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ['id', 'message_type', 'person_name', 'role_title', 'message_body', 'photo', 'order']

    def get_photo(self, obj):
        if obj.photo:
            request = self.context.get('request')
            return request.build_absolute_uri(obj.photo.url) if request else obj.photo.url
        return None
