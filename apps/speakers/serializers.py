"""
Speakers serializers - list, detail, and write serializers.
"""

from rest_framework import serializers

from apps.common.utils import get_file_url

from .models import Speaker


class SpeakerListSerializer(serializers.ModelSerializer):
    profile_image = serializers.SerializerMethodField()
    event_title = serializers.CharField(source='event.title', read_only=True)
    event_slug = serializers.CharField(source='event.slug', read_only=True)

    class Meta:
        model = Speaker
        fields = [
            'id', 'name', 'slug', 'designation', 'organization', 'profile_image', 'talk_title',
            'featured', 'event_title', 'event_slug', 'created_at', 'updated_at', 'is_active',
        ]

    def get_profile_image(self, obj):
        request = self.context.get('request')
        return get_file_url(request, obj.profile_image)


class SpeakerDetailSerializer(SpeakerListSerializer):
    class Meta(SpeakerListSerializer.Meta):
        fields = SpeakerListSerializer.Meta.fields + ['bio', 'linkedin', 'instagram', 'website', 'event']


class SpeakerWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Speaker
        fields = [
            'id', 'name', 'slug', 'designation', 'organization', 'bio', 'profile_image',
            'linkedin', 'instagram', 'website', 'talk_title', 'featured', 'event',
            'created_at', 'updated_at', 'is_active',
        ]
        read_only_fields = ['id', 'slug', 'created_at', 'updated_at', 'is_active']
