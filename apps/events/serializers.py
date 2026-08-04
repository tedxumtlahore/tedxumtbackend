"""
Events serializers - venues, events, and schedule items.
"""

from rest_framework import serializers

from apps.common.utils import get_file_url

from .models import Venue, Event, EventScheduleItem


class VenueSerializer(serializers.ModelSerializer):
    class Meta:
        model = Venue
        fields = ['id', 'name', 'address', 'city', 'google_maps', 'created_at', 'updated_at', 'is_active']


class EventScheduleItemSerializer(serializers.ModelSerializer):
    speaker_name = serializers.SerializerMethodField()

    class Meta:
        model = EventScheduleItem
        fields = [
            'id', 'title', 'speaker', 'speaker_name', 'start_time', 'end_time', 'description',
            'created_at', 'updated_at', 'is_active',
        ]

    def get_speaker_name(self, obj):
        if obj.speaker:
            return getattr(obj.speaker, 'name', None)
        return None


class EventListSerializer(serializers.ModelSerializer):
    venue_name = serializers.CharField(source='venue.name', read_only=True)
    venue_city = serializers.CharField(source='venue.city', read_only=True)
    featured_image = serializers.SerializerMethodField()
    banner_image = serializers.SerializerMethodField()
    speaker_count = serializers.SerializerMethodField()
    year = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = [
            'id', 'title', 'slug', 'short_description', 'featured_image', 'banner_image',
            'venue_name', 'venue_city', 'start_datetime', 'end_datetime', 'registration_url',
            'max_attendees', 'event_type', 'status', 'is_featured', 'speaker_count', 'year',
            'created_at', 'updated_at', 'is_active',
        ]

    def get_featured_image(self, obj):
        request = self.context.get('request')
        return get_file_url(request, obj.featured_image)

    def get_banner_image(self, obj):
        request = self.context.get('request')
        return get_file_url(request, obj.banner_image)

    def get_speaker_count(self, obj):
        if not obj.pk:
            return 0
        return obj.schedule_items.filter(speaker__isnull=False).count()

    def get_year(self, obj):
        return obj.start_datetime.year if obj.start_datetime else None


class EventWriteSerializer(serializers.ModelSerializer):
    venue = serializers.PrimaryKeyRelatedField(queryset=Venue.objects.all())

    class Meta:
        model = Event
        fields = [
            'id', 'title', 'slug', 'short_description', 'description', 'featured_image', 'banner_image',
            'venue', 'start_datetime', 'end_datetime', 'registration_url', 'max_attendees', 'event_type',
            'status', 'is_featured', 'created_at', 'updated_at', 'is_active',
        ]
        read_only_fields = ['id', 'slug', 'created_at', 'updated_at', 'is_active']


class EventDetailSerializer(EventListSerializer):
    venue = VenueSerializer(read_only=True)
    schedule_items = serializers.SerializerMethodField()

    class Meta(EventListSerializer.Meta):
        fields = EventListSerializer.Meta.fields + ['venue', 'description', 'schedule_items']

    def get_schedule_items(self, obj):
        if not obj.pk:
            return []
        items = obj.schedule_items.all()
        return EventScheduleItemSerializer(items, many=True, context=self.context).data
