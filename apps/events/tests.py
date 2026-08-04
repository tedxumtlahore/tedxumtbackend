from django.test import SimpleTestCase

from datetime import datetime, time, timezone

from .models import Venue, Event, EventScheduleItem
from .serializers import VenueSerializer, EventListSerializer, EventDetailSerializer, EventScheduleItemSerializer


class EventModelTests(SimpleTestCase):
    def test_event_type_choices_use_textchoices(self):
        self.assertEqual(Event.EventTypeChoices.FLAGSHIP, 'flagship')
        self.assertEqual(Event.StatusChoices.UPCOMING, 'upcoming')

    def test_event_slug_is_not_editable(self):
        self.assertFalse(Event._meta.get_field('slug').editable)


class EventSerializerTests(SimpleTestCase):
    def test_venue_serializer_includes_system_fields(self):
        venue = Venue(name='UMT Auditorium', address='UMT Campus', city='Lahore', google_maps='https://maps.google.com')
        serializer = VenueSerializer(venue)

        self.assertEqual(serializer.data['name'], 'UMT Auditorium')
        self.assertIn('created_at', serializer.data)

    def test_event_list_serializer_exposes_summary_fields(self):
        venue = Venue(name='UMT Auditorium', address='UMT Campus', city='Lahore', google_maps='https://maps.google.com')
        event = Event(
            title='Resonance 2026',
            short_description='A flagship TEDx event',
            description='Long description',
            venue=venue,
            start_datetime=datetime(2026, 11, 14, 10, 0, tzinfo=timezone.utc),
            end_datetime=datetime(2026, 11, 14, 17, 0, tzinfo=timezone.utc),
            registration_url='https://example.com/register',
            max_attendees=500,
            event_type=Event.EventTypeChoices.FLAGSHIP,
            status=Event.StatusChoices.UPCOMING,
            is_featured=True,
        )

        serializer = EventListSerializer(event)

        self.assertEqual(serializer.data['title'], 'Resonance 2026')
        self.assertEqual(serializer.data['venue_name'], 'UMT Auditorium')
        self.assertIn('speaker_count', serializer.data)

    def test_event_detail_serializer_includes_nested_fields(self):
        venue = Venue(name='UMT Auditorium', address='UMT Campus', city='Lahore', google_maps='https://maps.google.com')
        event = Event(
            title='Resonance 2026',
            short_description='A flagship TEDx event',
            description='Long description',
            venue=venue,
            start_datetime=datetime(2026, 11, 14, 10, 0, tzinfo=timezone.utc),
            end_datetime=datetime(2026, 11, 14, 17, 0, tzinfo=timezone.utc),
            registration_url='https://example.com/register',
            max_attendees=500,
            event_type=Event.EventTypeChoices.FLAGSHIP,
            status=Event.StatusChoices.UPCOMING,
            is_featured=True,
        )

        serializer = EventDetailSerializer(event)

        self.assertIn('venue', serializer.data)
        self.assertIn('schedule_items', serializer.data)

    def test_schedule_item_serializer_exposes_speaker_name(self):
        venue = Venue(name='UMT Auditorium', address='UMT Campus', city='Lahore', google_maps='https://maps.google.com')
        event = Event(
            title='Resonance 2026',
            short_description='A flagship TEDx event',
            description='Long description',
            venue=venue,
            start_datetime=datetime(2026, 11, 14, 10, 0, tzinfo=timezone.utc),
            end_datetime=datetime(2026, 11, 14, 17, 0, tzinfo=timezone.utc),
            registration_url='https://example.com/register',
            max_attendees=500,
            event_type=Event.EventTypeChoices.FLAGSHIP,
            status=Event.StatusChoices.UPCOMING,
            is_featured=True,
        )
        item = EventScheduleItem(
            event=event,
            title='Opening Remarks',
            start_time=time(10, 0),
            end_time=time(10, 30),
            description='Welcome',
        )

        serializer = EventScheduleItemSerializer(item)
        self.assertEqual(serializer.data['title'], 'Opening Remarks')
        self.assertIn('speaker_name', serializer.data)
