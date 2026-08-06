from datetime import datetime, time, timezone

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.test import SimpleTestCase
from django.urls import reverse
from rest_framework.test import APITestCase

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


class EventAPITests(APITestCase):
    def setUp(self):
        self.venue = Venue.objects.create(name='UMT Auditorium', address='UMT Campus', city='Lahore')
        self.upcoming = Event.objects.create(
            title='Resonance 2026', short_description='Flagship', description='Long',
            venue=self.venue,
            start_datetime=datetime(2026, 11, 14, 10, 0, tzinfo=timezone.utc),
            end_datetime=datetime(2026, 11, 14, 17, 0, tzinfo=timezone.utc),
            event_type=Event.EventTypeChoices.FLAGSHIP,
            status=Event.StatusChoices.UPCOMING, is_featured=True,
        )
        self.draft = Event.objects.create(
            title='Secret 2027', short_description='Draft', description='Long',
            venue=self.venue,
            start_datetime=datetime(2027, 11, 14, 10, 0, tzinfo=timezone.utc),
            end_datetime=datetime(2027, 11, 14, 17, 0, tzinfo=timezone.utc),
            event_type=Event.EventTypeChoices.TALKS,
        )

    def test_slug_is_generated_from_the_title(self):
        self.assertEqual(self.upcoming.slug, 'resonance-2026')

    def test_drafts_are_hidden_from_anonymous_users(self):
        response = self.client.get('/api/events/')

        self.assertEqual([e['title'] for e in response.data['results']], ['Resonance 2026'])

    def test_featured_endpoint_returns_flagged_events(self):
        response = self.client.get(reverse('api-featured-events'))

        self.assertEqual([e['title'] for e in response.data], ['Resonance 2026'])

    def test_detail_includes_schedule_and_speakers(self):
        EventScheduleItem.objects.create(
            event=self.upcoming, title='Opening Remarks', start_time=time(10, 0), end_time=time(10, 30),
        )

        response = self.client.get(f'/api/events/{self.upcoming.slug}/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['schedule_items']), 1)
        self.assertIn('speakers', response.data)
        self.assertEqual(response.data['venue']['name'], 'UMT Auditorium')

    def test_speaker_count_reflects_the_billed_lineup(self):
        from apps.speakers.models import Speaker

        for name in ('Amina Raza', 'Hamza Tariq'):
            Speaker.objects.create(
                name=name, designation='x', organization='x', bio='x',
                talk_title='x', event=self.upcoming,
            )

        listed = self.client.get('/api/events/').data['results'][0]
        detail = self.client.get(f'/api/events/{self.upcoming.slug}/').data

        # The list annotation and the detail fallback must agree.
        self.assertEqual(listed['speaker_count'], 2)
        self.assertEqual(detail['speaker_count'], 2)

    def test_speaker_count_ignores_inactive_speakers(self):
        from apps.speakers.models import Speaker

        Speaker.objects.create(
            name='Retired Speaker', designation='x', organization='x', bio='x',
            talk_title='x', event=self.upcoming, is_active=False,
        )

        listed = self.client.get('/api/events/').data['results'][0]
        self.assertEqual(listed['speaker_count'], 0)

    def test_year_is_derived_from_the_start_date(self):
        response = self.client.get('/api/events/')

        self.assertEqual(response.data['results'][0]['year'], 2026)

    def test_filter_events_by_status(self):
        Event.objects.create(
            title='Genesis 2024', short_description='Past', description='Long', venue=self.venue,
            start_datetime=datetime(2024, 11, 2, 10, 0, tzinfo=timezone.utc),
            end_datetime=datetime(2024, 11, 2, 17, 0, tzinfo=timezone.utc),
            event_type=Event.EventTypeChoices.FLAGSHIP, status=Event.StatusChoices.PAST,
        )

        response = self.client.get('/api/events/', {'status': 'past'})

        self.assertEqual([e['title'] for e in response.data['results']], ['Genesis 2024'])

    def test_options_endpoint_lists_choices(self):
        response = self.client.get('/api/events/options/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['event_types']), 6)
        self.assertEqual(len(response.data['statuses']), 4)

    def test_event_rejects_an_end_before_its_start(self):
        event = Event(
            title='Broken', short_description='x', description='x', venue=self.venue,
            start_datetime=datetime(2026, 11, 14, 17, 0, tzinfo=timezone.utc),
            end_datetime=datetime(2026, 11, 14, 10, 0, tzinfo=timezone.utc),
            event_type=Event.EventTypeChoices.TALKS,
        )

        with self.assertRaises(DjangoValidationError):
            event.full_clean()

    def test_schedule_item_rejects_an_end_before_its_start(self):
        item = EventScheduleItem(
            event=self.upcoming, title='Broken', start_time=time(11, 0), end_time=time(10, 0),
        )

        with self.assertRaises(DjangoValidationError):
            item.full_clean()

    def test_anonymous_users_cannot_create_events(self):
        response = self.client.post('/api/events/', {
            'title': 'Injected', 'short_description': 'x', 'description': 'x',
            'venue': self.venue.pk, 'event_type': 'talks',
            'start_datetime': '2026-01-01T10:00:00Z', 'end_datetime': '2026-01-01T12:00:00Z',
        }, format='json')

        self.assertEqual(response.status_code, 403)
        self.assertFalse(Event.objects.filter(title='Injected').exists())

    def test_anonymous_users_cannot_delete_events(self):
        response = self.client.delete(f'/api/events/{self.upcoming.slug}/')

        self.assertEqual(response.status_code, 403)
        self.assertTrue(Event.objects.filter(pk=self.upcoming.pk).exists())

    def test_staff_can_create_events(self):
        get_user_model().objects.create_superuser('organizer', 'o@example.com', 'pw-strong-123')
        self.client.login(username='organizer', password='pw-strong-123')

        response = self.client.post('/api/events/', {
            'title': 'Convergence 2025', 'short_description': 'x', 'description': 'x',
            'venue': self.venue.pk, 'event_type': 'talks', 'status': 'past',
            'start_datetime': '2025-11-08T10:00:00Z', 'end_datetime': '2025-11-08T17:00:00Z',
        }, format='json')

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Event.objects.get(title='Convergence 2025').slug, 'convergence-2025')

    def test_api_rejects_an_end_before_its_start(self):
        get_user_model().objects.create_superuser('organizer2', 'o2@example.com', 'pw-strong-123')
        self.client.login(username='organizer2', password='pw-strong-123')

        response = self.client.post('/api/events/', {
            'title': 'Backwards', 'short_description': 'x', 'description': 'x',
            'venue': self.venue.pk, 'event_type': 'talks',
            'start_datetime': '2026-01-01T12:00:00Z', 'end_datetime': '2026-01-01T10:00:00Z',
        }, format='json')

        self.assertEqual(response.status_code, 400)
