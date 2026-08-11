"""
Attendee account tests.

The bulk of these guard one property: an identity-keyed endpoint must never
become a way to read someone else's registration. Every other attendee endpoint
in this project is gated by an unguessable token, so `/me/registrations/` is the
one place where a filtering mistake would expose the attendee list.
"""

from django.contrib.auth.models import Group, User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.common.permissions import ORGANIZERS_GROUP, VOLUNTEERS_GROUP
from apps.ticketing.models import Registration
# Reused rather than re-derived: Event requires a venue and a valid datetime
# range, and duplicating that setup here would drift from the real one.
from apps.ticketing.tests import make_event

# DRF answers an unauthenticated request with 403, not 401, whenever the first
# authentication class is SessionAuthentication — it has no challenge to send,
# so it cannot return a WWW-Authenticate header. That is the project's setting,
# so 403 is the correct expectation here.
UNAUTHENTICATED = status.HTTP_403_FORBIDDEN


class AccountCreationTests(APITestCase):
    url = reverse('account-register')

    def test_creates_account_and_returns_tokens(self):
        response = self.client.post(
            self.url,
            {'full_name': 'Ayesha Khan', 'email': 'Ayesha@Example.com', 'password': 'not-a-real-password-4718'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('access', response.data['tokens'])
        self.assertIn('refresh', response.data['tokens'])

        user = User.objects.get(email='ayesha@example.com')
        self.assertEqual(user.username, 'ayesha@example.com', 'email should be normalised to lowercase')
        self.assertEqual(user.first_name, 'Ayesha')

    def test_new_account_has_no_privileges(self):
        """An attendee must not inherit staff, volunteer or organizer access."""
        self.client.post(
            self.url,
            {'full_name': 'Ayesha Khan', 'email': 'a@example.com', 'password': 'not-a-real-password-4718'},
            format='json',
        )
        user = User.objects.get(email='a@example.com')
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.groups.filter(name__in=[VOLUNTEERS_GROUP, ORGANIZERS_GROUP]).exists())

    def test_duplicate_email_rejected(self):
        payload = {'full_name': 'A', 'email': 'dup@example.com', 'password': 'not-a-real-password-4718'}
        self.client.post(self.url, payload, format='json')
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data['errors'])

    def test_duplicate_email_is_case_insensitive(self):
        self.client.post(
            self.url,
            {'full_name': 'A', 'email': 'dup@example.com', 'password': 'not-a-real-password-4718'},
            format='json',
        )
        response = self.client.post(
            self.url,
            {'full_name': 'B', 'email': 'DUP@Example.com', 'password': 'not-a-real-password-4718'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_weak_password_rejected(self):
        response = self.client.post(
            self.url,
            {'full_name': 'A', 'email': 'weak@example.com', 'password': '1234'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data['errors'])
        self.assertFalse(User.objects.filter(email='weak@example.com').exists())


class MyRegistrationsTests(APITestCase):
    url = reverse('account-registrations')

    def setUp(self):
        self.event = make_event()
        self.alice = User.objects.create_user('alice@example.com', password='not-a-real-password-4718')
        self.bob = User.objects.create_user('bob@example.com', password='not-a-real-password-4718')

        self.alice_reg = Registration.objects.create(
            event=self.event, full_name='Alice', email='alice@example.com',
            phone='03001234567', user=self.alice,
        )
        self.bob_reg = Registration.objects.create(
            event=self.event, full_name='Bob', email='bob@example.com',
            phone='03007654321', user=self.bob,
        )
        self.guest_reg = Registration.objects.create(
            event=self.event, full_name='Guest', email='guest@example.com',
            phone='03009999999',
        )

    def test_requires_authentication(self):
        self.assertEqual(self.client.get(self.url).status_code, UNAUTHENTICATED)

    def test_returns_only_the_callers_registrations(self):
        self.client.force_authenticate(self.alice)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        refs = {r['public_ref'] for r in response.data['results']}
        self.assertEqual(refs, {str(self.alice_reg.public_ref)})
        self.assertNotIn(str(self.bob_reg.public_ref), refs)
        self.assertNotIn(str(self.guest_reg.public_ref), refs)

    def test_unclaimed_registrations_belong_to_nobody(self):
        """A guest registration must not surface just because the email matches."""
        matching = User.objects.create_user('guest@example.com', password='not-a-real-password-4718')
        self.client.force_authenticate(matching)
        response = self.client.get(self.url)
        self.assertEqual(response.data['count'], 0)


class ClaimRegistrationTests(APITestCase):
    url = reverse('account-claim-registration')

    def setUp(self):
        self.event = make_event()
        self.alice = User.objects.create_user('alice@example.com', password='not-a-real-password-4718')
        self.bob = User.objects.create_user('bob@example.com', password='not-a-real-password-4718')
        self.guest_reg = Registration.objects.create(
            event=self.event, full_name='Guest', email='guest@example.com', phone='03009999999',
        )

    def test_claims_with_correct_public_ref(self):
        self.client.force_authenticate(self.alice)
        response = self.client.post(
            self.url, {'public_ref': str(self.guest_reg.public_ref)}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.guest_reg.refresh_from_db()
        self.assertEqual(self.guest_reg.user, self.alice)

    def test_unknown_reference_is_404(self):
        import uuid

        self.client.force_authenticate(self.alice)
        response = self.client.post(self.url, {'public_ref': str(uuid.uuid4())}, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_steal_a_claimed_registration(self):
        self.guest_reg.user = self.bob
        self.guest_reg.save(update_fields=['user'])

        self.client.force_authenticate(self.alice)
        response = self.client.post(
            self.url, {'public_ref': str(self.guest_reg.public_ref)}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data['code'], 'already_claimed')

        self.guest_reg.refresh_from_db()
        self.assertEqual(self.guest_reg.user, self.bob, 'owner must not change')

    def test_reclaiming_own_registration_is_idempotent(self):
        self.client.force_authenticate(self.alice)
        payload = {'public_ref': str(self.guest_reg.public_ref)}
        self.client.post(self.url, payload, format='json')
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_requires_authentication(self):
        response = self.client.post(
            self.url, {'public_ref': str(self.guest_reg.public_ref)}, format='json'
        )
        self.assertEqual(response.status_code, UNAUTHENTICATED)


class EventRegistrationLinkingTests(APITestCase):
    def setUp(self):
        self.event = make_event()
        self.user = User.objects.create_user('alice@example.com', password='not-a-real-password-4718')
        self.url = reverse('api-event-register', kwargs={'slug': self.event.slug})

    def test_signed_in_registration_is_linked(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            self.url,
            {'full_name': 'Alice', 'email': 'alice@example.com', 'phone': '03001234567'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Registration.objects.get(email='alice@example.com').user, self.user)

    def test_anonymous_registration_is_refused(self):
        """
        Tickets are delivered through the account, not by email, so a
        registration with no account attached is one its owner cannot reach.
        """
        response = self.client.post(
            self.url,
            {'full_name': 'Guest', 'email': 'guest@example.com', 'phone': '03001234567'},
            format='json',
        )
        self.assertEqual(response.status_code, UNAUTHENTICATED)
        self.assertFalse(Registration.objects.filter(email='guest@example.com').exists())

    def test_registering_for_someone_else_is_linked_to_the_buyer(self):
        """
        One account may register several people — a student buying for friends.
        The registration is filed under the buyer, who is the one who can
        retrieve it, regardless of whose email is on it.
        """
        self.client.force_authenticate(self.user)
        self.client.post(
            self.url,
            {'full_name': 'Friend', 'email': 'friend@example.com', 'phone': '03001234567'},
            format='json',
        )
        self.assertEqual(Registration.objects.get(email='friend@example.com').user, self.user)


class MeEndpointTests(APITestCase):
    url = reverse('account-me')

    def test_reports_roles(self):
        user = User.objects.create_user('vol@example.com', password='not-a-real-password-4718')
        user.groups.add(Group.objects.get_or_create(name=VOLUNTEERS_GROUP)[0])

        self.client.force_authenticate(user)
        response = self.client.get(self.url)
        self.assertTrue(response.data['is_volunteer'])
        self.assertFalse(response.data['is_organizer'])
        self.assertFalse(response.data['is_staff'])

    def test_plain_attendee_has_no_roles(self):
        user = User.objects.create_user('a@example.com', password='not-a-real-password-4718')
        self.client.force_authenticate(user)
        response = self.client.get(self.url)
        self.assertFalse(response.data['is_volunteer'])
        self.assertFalse(response.data['is_organizer'])
        self.assertFalse(response.data['is_staff'])

    def test_requires_authentication(self):
        self.assertEqual(self.client.get(self.url).status_code, UNAUTHENTICATED)
