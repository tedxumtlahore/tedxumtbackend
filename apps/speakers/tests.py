from datetime import datetime, timezone

from django.test import SimpleTestCase
from django.urls import reverse
from rest_framework.test import APITestCase

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


class SpeakerAPITests(APITestCase):
    def setUp(self):
        self.venue = Venue.objects.create(name='UMT Auditorium', address='UMT Campus', city='Lahore')
        self.event = Event.objects.create(
            title='Resonance 2026', short_description='Flagship', description='Long', venue=self.venue,
            start_datetime=datetime(2026, 11, 14, 10, 0, tzinfo=timezone.utc),
            end_datetime=datetime(2026, 11, 14, 17, 0, tzinfo=timezone.utc),
            event_type=Event.EventTypeChoices.FLAGSHIP, status=Event.StatusChoices.UPCOMING,
        )
        self.speaker = Speaker.objects.create(
            name='Dr. Amina Raza', designation='Cognitive Neuroscientist',
            organization='LUMS', bio='Bio', talk_title='The Architecture of Memory',
            featured=True, event=self.event,
        )
        Speaker.objects.create(
            name='Hidden Speaker', designation='x', organization='x', bio='x',
            talk_title='x', event=self.event, is_active=False,
        )

    def test_slug_is_generated_from_the_name(self):
        self.assertEqual(self.speaker.slug, 'dr-amina-raza')

    def test_duplicate_names_get_unique_slugs(self):
        duplicate = Speaker.objects.create(
            name='Dr. Amina Raza', designation='x', organization='x', bio='x',
            talk_title='x', event=self.event,
        )
        self.assertEqual(duplicate.slug, 'dr-amina-raza-1')

    def test_inactive_speakers_are_hidden(self):
        response = self.client.get('/api/speakers/')

        self.assertEqual([s['name'] for s in response.data['results']], ['Dr. Amina Raza'])

    def test_detail_is_looked_up_by_slug(self):
        response = self.client.get(f'/api/speakers/{self.speaker.slug}/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['bio'], 'Bio')
        self.assertEqual(response.data['event_title'], 'Resonance 2026')

    def test_featured_endpoint_returns_flagged_speakers(self):
        response = self.client.get(reverse('api-featured-speakers'))

        self.assertEqual([s['name'] for s in response.data], ['Dr. Amina Raza'])

    def test_filter_speakers_by_event_slug(self):
        response = self.client.get('/api/speakers/', {'event': 'resonance-2026'})

        self.assertEqual(len(response.data['results']), 1)

    def test_search_matches_the_talk_title(self):
        response = self.client.get('/api/speakers/', {'search': 'Architecture'})

        self.assertEqual([s['name'] for s in response.data['results']], ['Dr. Amina Raza'])

    def test_event_detail_lists_its_speakers(self):
        response = self.client.get(f'/api/events/{self.event.slug}/')

        self.assertEqual([s['name'] for s in response.data['speakers']], ['Dr. Amina Raza'])

    def test_anonymous_users_cannot_create_speakers(self):
        response = self.client.post('/api/speakers/', {
            'name': 'Injected', 'designation': 'x', 'organization': 'x', 'bio': 'x',
            'talk_title': 'x', 'event': self.event.pk,
        }, format='json')

        self.assertEqual(response.status_code, 403)
        self.assertFalse(Speaker.objects.filter(name='Injected').exists())
