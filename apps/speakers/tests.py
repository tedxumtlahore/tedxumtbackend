from datetime import datetime, timezone

from django.test import SimpleTestCase

from apps.events.models import Event, Venue

from .models import Speaker
from .serializers import SpeakerListSerializer, SpeakerDetailSerializer, SpeakerWriteSerializer


class SpeakerModelTests(SimpleTestCase):
    def test_speaker_slug_is_not_editable(self):
        self.assertFalse(Speaker._meta.get_field('slug').editable)

    def test_speaker_related_name_points_to_event(self):
        field = Speaker._meta.get_field('event')
        self.assertEqual(field.remote_field.related_name, 'speakers')


class SpeakerSerializerTests(SimpleTestCase):
    def build_event(self):
        venue = Venue(name='UMT Auditorium', address='UMT Campus', city='Lahore', google_maps='https://maps.google.com')
        return Event(
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

    def test_list_serializer_exposes_summary_fields(self):
        speaker = Speaker(
            name='Ayesha Bint e Hamid',
            designation='President',
            organization='TEDxUMT Lahore',
            bio='Bio',
            talk_title='Ideas in Motion',
            featured=True,
            event=self.build_event(),
        )

        serializer = SpeakerListSerializer(speaker)

        self.assertEqual(serializer.data['name'], 'Ayesha Bint e Hamid')
        self.assertIn('event_title', serializer.data)

    def test_detail_serializer_includes_long_form_fields(self):
        speaker = Speaker(
            name='Ayesha Bint e Hamid',
            designation='President',
            organization='TEDxUMT Lahore',
            bio='Bio',
            talk_title='Ideas in Motion',
            linkedin='https://linkedin.com/in/example',
            instagram='https://instagram.com/example',
            website='https://example.com',
            featured=True,
            event=self.build_event(),
        )

        serializer = SpeakerDetailSerializer(speaker)

        self.assertEqual(serializer.data['bio'], 'Bio')
        self.assertIn('linkedin', serializer.data)

    def test_write_serializer_includes_event_relationship(self):
        serializer = SpeakerWriteSerializer()
        self.assertIn('event', serializer.fields)
