from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from apps.common.testing import login_as_staff

from .models import (
    ContactMessage,
    NewsletterSubscriber,
    PartnerApplication,
    SpeakerApplication,
    SubmissionStatusChoices,
    VolunteerApplication,
)

VALID_TALK_SUMMARY = (
    'Memory is not a recording device but a reconstruction engine, and that changes '
    'everything about how we should design education and technology around it.'
)

# Throttling is a production concern; these tests exercise validation and permissions.
NO_THROTTLE = {'DEFAULT_THROTTLE_RATES': {'anon': None, 'submission': None, 'newsletter': None}}


class SubmissionModelTests(TestCase):
    def test_submissions_default_to_new_status(self):
        message = ContactMessage.objects.create(
            name='Ali', email='ali@example.com', subject='Hi', message='Hello there'
        )
        self.assertEqual(message.status, SubmissionStatusChoices.NEW)
        self.assertFalse(message.is_read)

    def test_newsletter_email_is_unique(self):
        NewsletterSubscriber.objects.create(email='a@example.com')
        self.assertEqual(NewsletterSubscriber.objects.filter(email='a@example.com').count(), 1)

    def test_str_representations(self):
        application = SpeakerApplication.objects.create(
            full_name='Amina Raza', email='a@example.com',
            talk_title='The Architecture of Memory', talk_summary=VALID_TALK_SUMMARY,
        )
        self.assertEqual(str(application), 'Amina Raza — The Architecture of Memory')


@override_settings(REST_FRAMEWORK=NO_THROTTLE)
class ContactAPITests(APITestCase):
    def test_valid_message_is_accepted(self):
        response = self.client.post(reverse('api-contact'), {
            'name': 'Ali Raza',
            'email': '  ALI@Example.com ',
            'subject': 'Speaking enquiry',
            'message': 'I would like to know more about applying to speak next year.',
        }, format='json')

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data['success'])
        self.assertEqual(ContactMessage.objects.get().email, 'ali@example.com')

    def test_short_message_is_rejected(self):
        response = self.client.post(reverse('api-contact'), {
            'name': 'Ali', 'email': 'ali@example.com', 'subject': 'Hi', 'message': 'too short',
        }, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertIn('message', response.data)

    def test_invalid_email_is_rejected(self):
        response = self.client.post(reverse('api-contact'), {
            'name': 'Ali', 'email': 'not-an-email', 'subject': 'Hello',
            'message': 'A perfectly long enough message body.',
        }, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertIn('email', response.data)

    def test_status_cannot_be_set_by_the_submitter(self):
        self.client.post(reverse('api-contact'), {
            'name': 'Ali Raza', 'email': 'ali@example.com', 'subject': 'Hello',
            'message': 'A perfectly long enough message body.',
            'status': SubmissionStatusChoices.ACCEPTED,
        }, format='json')

        self.assertEqual(ContactMessage.objects.get().status, SubmissionStatusChoices.NEW)

    def test_anonymous_users_cannot_read_the_inbox(self):
        ContactMessage.objects.create(
            name='Ali', email='ali@example.com', subject='Hi', message='Hello there'
        )

        response = self.client.get('/api/contact-messages/')

        self.assertEqual(response.status_code, 403)

    def test_staff_can_read_the_inbox(self):
        ContactMessage.objects.create(
            name='Ali', email='ali@example.com', subject='Hi', message='Hello there'
        )
        login_as_staff(self.client, 'admin1')

        response = self.client.get('/api/contact-messages/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)


@override_settings(REST_FRAMEWORK=NO_THROTTLE)
class NewsletterAPITests(APITestCase):
    def test_subscribe_creates_a_subscriber(self):
        response = self.client.post(reverse('api-newsletter'), {'email': 'reader@example.com'}, format='json')

        self.assertEqual(response.status_code, 201)
        self.assertTrue(NewsletterSubscriber.objects.get(email='reader@example.com').is_subscribed)

    def test_subscribing_twice_does_not_error(self):
        self.client.post(reverse('api-newsletter'), {'email': 'reader@example.com'}, format='json')
        response = self.client.post(reverse('api-newsletter'), {'email': 'reader@example.com'}, format='json')

        self.assertEqual(response.status_code, 201)
        self.assertEqual(NewsletterSubscriber.objects.count(), 1)

    def test_resubscribing_reactivates_a_removed_address(self):
        NewsletterSubscriber.objects.create(email='reader@example.com', is_subscribed=False)

        self.client.post(reverse('api-newsletter'), {'email': 'reader@example.com'}, format='json')

        self.assertTrue(NewsletterSubscriber.objects.get(email='reader@example.com').is_subscribed)

    def test_unsubscribe_marks_the_address_inactive(self):
        NewsletterSubscriber.objects.create(email='reader@example.com')

        response = self.client.post(
            reverse('api-newsletter-unsubscribe'), {'email': 'reader@example.com'}, format='json'
        )

        self.assertEqual(response.status_code, 200)
        subscriber = NewsletterSubscriber.objects.get(email='reader@example.com')
        self.assertFalse(subscriber.is_subscribed)
        self.assertIsNotNone(subscriber.unsubscribed_at)

    def test_subscriber_list_is_staff_only(self):
        response = self.client.get('/api/newsletter-subscribers/')

        self.assertEqual(response.status_code, 403)


@override_settings(REST_FRAMEWORK=NO_THROTTLE)
class ApplicationAPITests(APITestCase):
    def test_speaker_application_requires_a_substantial_summary(self):
        response = self.client.post(reverse('api-apply-speaker'), {
            'full_name': 'Amina Raza', 'email': 'amina@example.com',
            'talk_title': 'Memory', 'talk_summary': 'Too short.',
        }, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertIn('talk_summary', response.data)

    def test_valid_speaker_application_is_stored(self):
        response = self.client.post(reverse('api-apply-speaker'), {
            'full_name': 'Amina Raza', 'email': 'amina@example.com',
            'talk_title': 'The Architecture of Memory', 'talk_summary': VALID_TALK_SUMMARY,
        }, format='json')

        self.assertEqual(response.status_code, 201)
        self.assertEqual(SpeakerApplication.objects.count(), 1)

    def test_volunteer_application_is_stored(self):
        response = self.client.post(reverse('api-apply-volunteer'), {
            'full_name': 'Talha Mir', 'email': 'talha@example.com',
            'preferred_department': 'Operations', 'availability': 'part_time',
            'motivation': 'I want to help run the best student event in Lahore.',
        }, format='json')

        self.assertEqual(response.status_code, 201)
        self.assertEqual(VolunteerApplication.objects.count(), 1)

    def test_volunteer_application_rejects_an_unknown_availability(self):
        response = self.client.post(reverse('api-apply-volunteer'), {
            'full_name': 'Talha Mir', 'email': 'talha@example.com',
            'availability': 'whenever',
            'motivation': 'I want to help run the best student event in Lahore.',
        }, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertIn('availability', response.data)

    def test_partner_application_is_stored(self):
        response = self.client.post(reverse('api-apply-partner'), {
            'organization_name': 'Meridian Bank', 'contact_person': 'Sara Khan',
            'email': 'sara@meridian.example', 'partnership_type': 'sponsor',
            'proposal': 'We would like to discuss the Title sponsorship package for 2026.',
        }, format='json')

        self.assertEqual(response.status_code, 201)
        self.assertEqual(PartnerApplication.objects.count(), 1)

    def test_application_options_endpoint_lists_choices(self):
        response = self.client.get(reverse('api-apply-options'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['availability']), 3)
        self.assertEqual(len(response.data['partnership_types']), 5)

    def test_applications_are_not_publicly_readable(self):
        SpeakerApplication.objects.create(
            full_name='Amina Raza', email='amina@example.com',
            talk_title='Memory', talk_summary=VALID_TALK_SUMMARY,
        )

        response = self.client.get('/api/speaker-applications/')

        self.assertEqual(response.status_code, 403)


class SubmissionThrottleTests(APITestCase):
    """
    DRF reads DEFAULT_THROTTLE_RATES into a class attribute at import time, so
    override_settings cannot reach it — the rate is patched on the class instead.
    """

    def setUp(self):
        from rest_framework.throttling import SimpleRateThrottle

        from .throttling import SubmissionRateThrottle

        self.throttle_cls = SubmissionRateThrottle
        self.original_rates = dict(SimpleRateThrottle.THROTTLE_RATES)
        SimpleRateThrottle.THROTTLE_RATES = {**self.original_rates, 'submission': '2/day'}
        SimpleRateThrottle.cache.clear()

    def tearDown(self):
        from rest_framework.throttling import SimpleRateThrottle

        SimpleRateThrottle.THROTTLE_RATES = self.original_rates
        SimpleRateThrottle.cache.clear()

    def test_submissions_are_rate_limited(self):
        payload = {
            'name': 'Ali Raza', 'email': 'ali@example.com', 'subject': 'Hello',
            'message': 'A perfectly long enough message body.',
        }

        self.assertEqual(self.client.post(reverse('api-contact'), payload, format='json').status_code, 201)
        self.assertEqual(self.client.post(reverse('api-contact'), payload, format='json').status_code, 201)
        self.assertEqual(self.client.post(reverse('api-contact'), payload, format='json').status_code, 429)

    def test_staff_are_exempt_from_the_submission_throttle(self):
        login_as_staff(self.client, 'admin2')
        payload = {
            'name': 'Ali Raza', 'email': 'ali@example.com', 'subject': 'Hello',
            'message': 'A perfectly long enough message body.',
        }

        for _ in range(4):
            response = self.client.post(reverse('api-contact'), payload, format='json')

        self.assertEqual(response.status_code, 201)
