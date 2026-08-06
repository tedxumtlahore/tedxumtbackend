"""
Events serializers - venues, events, and schedule items.
"""

from rest_framework import serializers

from apps.common.utils import get_file_url

from .models import Event, EventScheduleItem, Venue


class VenueSerializer(serializers.ModelSerializer):
    class Meta:
        model = Venue
        fields = ['id', 'name', 'address', 'city', 'google_maps', 'created_at', 'updated_at', 'is_active']


class EventScheduleItemSerializer(serializers.ModelSerializer):
    speaker_name = serializers.SerializerMethodField()
    speaker_slug = serializers.CharField(source='speaker.slug', read_only=True)

    class Meta:
        model = EventScheduleItem
        fields = [
            'id', 'event', 'title', 'speaker', 'speaker_name', 'speaker_slug',
            'start_time', 'end_time', 'description',
            'created_at', 'updated_at', 'is_active',
        ]

    def get_speaker_name(self, obj):
        return getattr(obj.speaker, 'name', None) if obj.speaker else None

    def validate(self, attrs):
        start = attrs.get('start_time', getattr(self.instance, 'start_time', None))
        end = attrs.get('end_time', getattr(self.instance, 'end_time', None))
        if start and end and end <= start:
            raise serializers.ValidationError({'end_time': 'The session must end after it starts.'})
        return attrs


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
        return get_file_url(self.context.get('request'), obj.featured_image)

    def get_banner_image(self, obj):
        return get_file_url(self.context.get('request'), obj.banner_image)

    def get_speaker_count(self, obj):
        annotated_count = getattr(obj, 'speaker_count', None)
        if annotated_count is not None:
            return annotated_count
        if not obj.pk:
            return 0
        # Same definition as the list annotation: the billed lineup.
        return obj.speakers.filter(is_active=True).count()

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
        read_only_fields = ['id', 'slug', 'created_at', 'updated_at']

    def validate(self, attrs):
        start = attrs.get('start_datetime', getattr(self.instance, 'start_datetime', None))
        end = attrs.get('end_datetime', getattr(self.instance, 'end_datetime', None))
        if start and end and end <= start:
            raise serializers.ValidationError({'end_datetime': 'The event must end after it starts.'})
        return attrs


class EventDetailSerializer(EventListSerializer):
    venue = VenueSerializer(read_only=True)
    schedule_items = serializers.SerializerMethodField()
    speakers = serializers.SerializerMethodField()

    class Meta(EventListSerializer.Meta):
        fields = EventListSerializer.Meta.fields + [
            'venue', 'description', 'schedule_items', 'speakers',
        ]

    def get_schedule_items(self, obj):
        if not obj.pk:
            return []
        items = [i for i in obj.schedule_items.all() if i.is_active]
        return EventScheduleItemSerializer(items, many=True, context=self.context).data

    def get_speakers(self, obj):
        if not obj.pk:
            return []
        # Imported here to keep the events app importable on its own.
        from apps.speakers.serializers import SpeakerListSerializer

        speakers = obj.speakers.filter(is_active=True).select_related('event')
        return SpeakerListSerializer(speakers, many=True, context=self.context).data
