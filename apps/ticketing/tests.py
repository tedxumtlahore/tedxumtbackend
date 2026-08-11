"""
Ticketing tests.

The first class covers the five properties the whole feature rests on; if any
of those break, the system is worse than useless (double entry, oversold room,
free tickets). The rest cover the PRD's edge cases and the API surface.
"""

from datetime import datetime, timedelta
from datetime import timezone as dt_timezone
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.common.permissions import ORGANIZERS_GROUP, VOLUNTEERS_GROUP
from apps.events.models import Event, Venue
from apps.ticketing.models import CheckInLog, Order, Registration, Ticket, hash_identifier
from apps.ticketing.services import TicketingError, check_in, mark_paid, register

# Merged into the real settings, not substituted for them. Replacing the whole
# REST_FRAMEWORK dict silently drops EXCEPTION_HANDLER, and the tests would then
# assert against DRF's default error shape rather than the one we actually ship.
NO_THROTTLE = {
    **settings.REST_FRAMEWORK,
    'DEFAULT_THROTTLE_RATES': {
        'anon': None, 'user': None, 'submission': None,
        'newsletter': None, 'registration': None, 'checkin': None,
    },
}

VALID = {
    'full_name': 'Ayesha Khan',
    'email': 'ayesha@example.com',
    # Deliberately shares no digit run with the CNIC, so the leak assertions
    # below cannot pass or fail by coincidence.
    'phone': '+92 300 8880000',
    'cnic': '35202-1234567-8',
}


def make_event(**overrides):
    venue = Venue.objects.filter(name='UMT Auditorium').first() or Venue.objects.create(
        name='UMT Auditorium', address='UMT Campus', city='Lahore'
    )
    defaults = {
        'title': 'Resonance 2026',
        'short_description': 'Flagship',
        'description': 'Long',
        'venue': venue,
        'start_datetime': timezone.now() + timedelta(days=30),
        'end_datetime': timezone.now() + timedelta(days=30, hours=7),
        'event_type': Event.EventTypeChoices.FLAGSHIP,
        'status': Event.StatusChoices.UPCOMING,
        'registration_enabled': True,
        'ticket_price': Decimal('0.00'),
    }
    defaults.update(overrides)
    return Event.objects.create(**defaults)


class PaidWithoutTicketRepairTests(TestCase):
    """
    An order whose status column was written directly, bypassing `mark_paid`.

    Reachable from an editable admin dropdown, a data migration, or a manual SQL
    fix. The old code returned None here and left a paying attendee with no
    ticket; `mark_paid` now finishes the job instead.
    """

    def setUp(self):
        self.event = make_event()
        self.registration, self.order, _ = register(self.event, **VALID)

    def _corrupt(self):
        """Exactly what the admin dropdown used to do: set the column, nothing else."""
        Order.objects.filter(pk=self.order.pk).update(status=Order.Status.PAID)
        Ticket.objects.filter(registration=self.registration).delete()
        self.order.refresh_from_db()

    def test_paid_order_with_no_ticket_gets_one(self):
        self._corrupt()
        self.assertFalse(Ticket.objects.filter(registration=self.registration).exists())

        ticket = mark_paid(self.order)

        self.assertIsNotNone(ticket, 'must not hand back None to a paying attendee')
        self.assertTrue(Ticket.objects.filter(registration=self.registration).exists())

    def test_repair_also_fixes_the_registration_and_paid_at(self):
        self._corrupt()
        Registration.objects.filter(pk=self.registration.pk).update(
            status=Registration.Status.PENDING
        )

        mark_paid(self.order)

        self.registration.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(self.registration.status, Registration.Status.CONFIRMED)
        self.assertIsNotNone(self.order.paid_at, 'paid_at must be backfilled')

    def test_a_healthy_paid_order_is_untouched(self):
        """Idempotency must survive the repair path — no second ticket, ever."""
        original = Ticket.objects.get(registration=self.registration)

        again = mark_paid(self.order)

        self.assertEqual(again.pk, original.pk)
        self.assertEqual(Ticket.objects.filter(registration=self.registration).count(), 1)


def make_attendee(username='attendee@example.com'):
    """
    A plain signed-in visitor: no staff flag, no groups.

    Registration requires an account now, so API tests that post to the register
    endpoint need one. Deliberately privilege-free, so these tests cannot pass
    by accident on the strength of some other permission.
    """
    return get_user_model().objects.create_user(username=username, password='x' * 20)


def make_volunteer(username='vol', group=VOLUNTEERS_GROUP):
    user = get_user_model().objects.create_user(username=username, password='x' * 20)
    user.groups.add(Group.objects.get(name=group))
    return user


class CorrectnessPropertyTests(TestCase):
    """The five guarantees from the implementation plan."""

    def setUp(self):
        self.event = make_event()

    # 1 ─ a ticket can never be used twice
    def test_a_ticket_cannot_be_checked_in_twice(self):
        registration, _, _ = register(self.event, **VALID)
        ticket = registration.ticket
        volunteer = make_volunteer()

        first, first_result = check_in(ticket.qr_token, volunteer=volunteer)
        second, second_result = check_in(ticket.qr_token, volunteer=volunteer)

        self.assertEqual(first_result, CheckInLog.Result.ALLOWED)
        self.assertEqual(second_result, CheckInLog.Result.DUPLICATE)
        self.assertEqual(CheckInLog.objects.filter(result=CheckInLog.Result.ALLOWED).count(), 1)

    def test_concurrent_scans_admit_exactly_one(self):
        """
        The real race: two volunteers scan the same QR at the same moment.

        `check_in` uses a conditional UPDATE, so the second caller matches zero
        rows. A read-then-write implementation would let both through — this
        test is what stops that regressing.
        """
        registration, _, _ = register(self.event, **VALID)
        ticket = registration.ticket
        volunteer = make_volunteer()

        # Simulate the interleaving deterministically: both callers observed the
        # ticket as un-checked-in, then both try to consume it.
        results = []
        for _ in range(2):
            updated = Ticket.objects.filter(pk=ticket.pk, checked_in=False).update(
                checked_in=True, checked_in_at=timezone.now(), checked_in_by=volunteer
            )
            results.append(updated)

        self.assertEqual(results, [1, 0], 'exactly one scan may consume the ticket')

    # 2 ─ the room cannot oversell
    def test_capacity_is_enforced(self):
        event = make_event(title='Tiny Room', max_attendees=1)
        register(event, **VALID)

        with self.assertRaises(TicketingError) as ctx:
            register(event, full_name='Second Person', email='second@example.com', phone='03001234567')

        self.assertEqual(ctx.exception.code, 'registration_closed')
        self.assertIn('sold out', ctx.exception.message.lower())
        self.assertEqual(Registration.objects.filter(event=event).count(), 1)

    def test_an_expired_hold_releases_its_seat(self):
        event = make_event(
            title='Held Room', max_attendees=1,
            ticket_price=Decimal('500.00'), registration_hold_minutes=30,
        )
        first, _, _ = register(event, **VALID)
        # The first registration is pending (paid events await confirmation).
        self.assertEqual(first.status, Registration.Status.PENDING)

        # Wind its hold into the past; the seat should come back.
        Registration.objects.filter(pk=first.pk).update(
            hold_expires_at=timezone.now() - timedelta(minutes=1)
        )

        second, _, _ = register(
            event, full_name='Second Person', email='second@example.com', phone='03001234567'
        )
        self.assertEqual(second.status, Registration.Status.PENDING)
        first.refresh_from_db()
        self.assertEqual(first.status, Registration.Status.EXPIRED)

    # 3 ─ no ticket without payment
    def test_a_paid_event_issues_no_ticket_until_the_order_is_paid(self):
        event = make_event(title='Paid Event', ticket_price=Decimal('1500.00'))

        registration, order, instructions = register(event, **VALID)

        self.assertEqual(order.status, Order.Status.AWAITING_CONFIRMATION)
        self.assertFalse(Ticket.objects.filter(registration=registration).exists())
        self.assertEqual(instructions.kind, 'instructions')

    def test_confirming_payment_issues_exactly_one_ticket(self):
        event = make_event(title='Paid Event', ticket_price=Decimal('1500.00'))
        registration, order, _ = register(event, **VALID)

        ticket = mark_paid(order, reference='BANK-123')
        again = mark_paid(order, reference='BANK-123')

        self.assertEqual(ticket.pk, again.pk, 'confirming twice must not mint a second ticket')
        self.assertEqual(Ticket.objects.filter(registration=registration).count(), 1)
        registration.refresh_from_db()
        self.assertEqual(registration.status, Registration.Status.CONFIRMED)

    def test_issuing_a_ticket_for_an_unpaid_order_is_refused(self):
        from apps.ticketing.services import issue_ticket

        event = make_event(title='Paid Event', ticket_price=Decimal('1500.00'))
        registration, _, _ = register(event, **VALID)

        with self.assertRaises(TicketingError):
            issue_ticket(registration)

    # 4 ─ the client never asserts payment status (see ClientCannotAssertPaymentTests)

    # 5 ─ ticket numbers are unique and sequential per event
    def test_ticket_numbers_are_sequential_per_event(self):
        other = make_event(title='Second Event')
        numbers = []
        for i in range(3):
            registration, _, _ = register(
                self.event, full_name=f'P{i}', email=f'p{i}@example.com', phone='03001234567'
            )
            numbers.append(registration.ticket.ticket_number)

        first_of_other, _, _ = register(
            other, full_name='Q', email='q@example.com', phone='03001234567'
        )

        year = self.event.start_datetime.year
        self.assertEqual(numbers, [f'TEDX{year}-0001', f'TEDX{year}-0002', f'TEDX{year}-0003'])
        # A second event restarts its own sequence.
        self.assertTrue(first_of_other.ticket.ticket_number.endswith('-0001'))
        self.assertEqual(Ticket.objects.values('ticket_number').distinct().count(), 4)

    def test_two_events_in_one_year_do_not_collide(self):
        """
        The year-derived prefix is shared by every event in that year, so
        without a per-event discriminator both would issue TEDX2026-0001 and
        violate the unique constraint on ticket_number.
        """
        second = make_event(title='Same Year Workshop')
        self.assertEqual(self.event.start_datetime.year, second.start_datetime.year)

        first_reg, _, _ = register(self.event, **VALID)
        second_reg, _, _ = register(
            second, full_name='Other', email='other@example.com', phone='03001234567'
        )

        self.assertNotEqual(
            first_reg.ticket.ticket_number, second_reg.ticket.ticket_number
        )
        year = self.event.start_datetime.year
        self.assertEqual(first_reg.ticket.ticket_number, f'TEDX{year}-0001')
        self.assertEqual(second_reg.ticket.ticket_number, f'TEDX{year}-2-0001')

    def test_an_explicit_prefix_avoids_the_discriminator(self):
        second = make_event(title='Workshop', ticket_prefix='TEDXWORKSHOP')

        first_reg, _, _ = register(self.event, **VALID)
        second_reg, _, _ = register(
            second, full_name='Other', email='other@example.com', phone='03001234567'
        )

        self.assertEqual(second_reg.ticket.ticket_number, 'TEDXWORKSHOP-0001')
        self.assertNotEqual(first_reg.ticket.ticket_number, second_reg.ticket.ticket_number)

    def test_the_prefix_survives_a_later_event_edit(self):
        """Ticket numbers already in attendees' hands must not change meaning."""
        registration, _, _ = register(self.event, **VALID)
        original = registration.ticket.ticket_number

        self.event.ticket_prefix = 'RENAMED'
        self.event.save()
        second, _, _ = register(
            self.event, full_name='Other', email='other@example.com', phone='03001234567'
        )

        self.assertEqual(registration.ticket.ticket_number, original)
        self.assertTrue(second.ticket.ticket_number.startswith(original.rsplit('-', 1)[0]))


class PIIHandlingTests(TestCase):
    def test_the_raw_cnic_is_never_stored(self):
        event = make_event()
        registration, _, _ = register(event, **VALID)

        self.assertEqual(registration.cnic_last4, '5678')
        self.assertNotIn('35202', registration.cnic_hash)
        self.assertEqual(len(registration.cnic_hash), 64)
        # Nothing on the row holds the number itself.
        stored = ' '.join(str(v) for v in Registration.objects.filter(pk=registration.pk).values()[0].values())
        self.assertNotIn('3520212345678', stored.replace('-', ''))

    def test_hashing_ignores_punctuation_so_dedupe_still_catches_it(self):
        with_dashes, _ = hash_identifier('35202-1234567-8')
        without, _ = hash_identifier('3520212345678')
        self.assertEqual(with_dashes, without)

    def test_a_blank_cnic_hashes_to_nothing(self):
        self.assertEqual(hash_identifier(''), ('', ''))
        self.assertEqual(hash_identifier(None), ('', ''))


class DuplicateRegistrationTests(TestCase):
    def setUp(self):
        self.event = make_event()

    def test_the_same_email_cannot_register_twice(self):
        register(self.event, **VALID)

        with self.assertRaises(TicketingError) as ctx:
            register(self.event, **{**VALID, 'cnic': '35202-9999999-9'})

        self.assertEqual(ctx.exception.code, 'duplicate_email')

    def test_the_same_cnic_cannot_register_twice(self):
        register(self.event, **VALID)

        with self.assertRaises(TicketingError) as ctx:
            register(self.event, **{**VALID, 'email': 'different@example.com'})

        self.assertEqual(ctx.exception.code, 'duplicate_cnic')

    def test_email_matching_ignores_case(self):
        register(self.event, **VALID)

        with self.assertRaises(TicketingError):
            register(self.event, **{**VALID, 'email': 'AYESHA@EXAMPLE.COM', 'cnic': ''})

    def test_the_same_person_may_register_for_a_different_event(self):
        register(self.event, **VALID)
        other = make_event(title='Another Event')

        registration, _, _ = register(other, **VALID)

        self.assertEqual(registration.event, other)

    def test_a_cancelled_registration_frees_the_email(self):
        first, _, _ = register(self.event, **VALID)
        Registration.objects.filter(pk=first.pk).update(status=Registration.Status.CANCELLED)

        # The unique constraint still applies, so re-registering the same email
        # must fail loudly rather than corrupting the table.
        with self.assertRaises(Exception):
            register(self.event, **VALID)


class RegistrationWindowTests(TestCase):
    def test_registration_is_closed_when_the_switch_is_off(self):
        event = make_event(registration_enabled=False)

        with self.assertRaises(TicketingError) as ctx:
            register(event, **VALID)

        self.assertEqual(ctx.exception.code, 'registration_closed')

    def test_registration_is_closed_before_it_opens(self):
        event = make_event(registration_opens_at=timezone.now() + timedelta(days=1))

        with self.assertRaises(TicketingError):
            register(event, **VALID)

    def test_registration_is_closed_after_the_deadline(self):
        event = make_event(registration_closes_at=timezone.now() - timedelta(hours=1))

        with self.assertRaises(TicketingError) as ctx:
            register(event, **VALID)

        self.assertIn('closed', ctx.exception.message.lower())

    def test_a_cancelled_event_takes_no_registrations(self):
        event = make_event(status=Event.StatusChoices.CANCELLED)

        with self.assertRaises(TicketingError):
            register(event, **VALID)

    def test_a_draft_event_takes_no_registrations(self):
        event = make_event(status=Event.StatusChoices.DRAFT)

        with self.assertRaises(TicketingError):
            register(event, **VALID)


class CheckInLogicTests(TestCase):
    def setUp(self):
        self.event = make_event()
        self.volunteer = make_volunteer()
        self.registration, _, _ = register(self.event, **VALID)
        self.ticket = self.registration.ticket

    def test_an_unknown_token_is_rejected_and_logged(self):
        ticket, result = check_in('not-a-real-token', volunteer=self.volunteer)

        self.assertIsNone(ticket)
        self.assertEqual(result, CheckInLog.Result.INVALID)
        self.assertEqual(CheckInLog.objects.filter(result=CheckInLog.Result.INVALID).count(), 1)

    def test_a_scanned_url_resolves_to_its_ticket(self):
        url = f'https://tedxumt.com/checkin/{self.ticket.qr_token}'

        _, result = check_in(url, volunteer=self.volunteer)

        self.assertEqual(result, CheckInLog.Result.ALLOWED)

    def test_a_ticket_for_another_event_is_rejected(self):
        other = make_event(title='Different Event')

        _, result = check_in(self.ticket.qr_token, volunteer=self.volunteer, event=other)

        self.assertEqual(result, CheckInLog.Result.WRONG_EVENT)

    def test_a_cancelled_registration_is_rejected_at_the_door(self):
        Registration.objects.filter(pk=self.registration.pk).update(
            status=Registration.Status.CANCELLED
        )

        _, result = check_in(self.ticket.qr_token, volunteer=self.volunteer)

        self.assertEqual(result, CheckInLog.Result.CANCELLED)

    def test_every_attempt_is_logged_including_failures(self):
        check_in('garbage', volunteer=self.volunteer)
        check_in(self.ticket.qr_token, volunteer=self.volunteer)
        check_in(self.ticket.qr_token, volunteer=self.volunteer)

        self.assertEqual(CheckInLog.objects.count(), 3)
        self.assertEqual(
            list(CheckInLog.objects.order_by('created_at', 'pk').values_list('result', flat=True)),
            [CheckInLog.Result.INVALID, CheckInLog.Result.ALLOWED, CheckInLog.Result.DUPLICATE],
        )

    def test_verification_does_not_consume_the_ticket(self):
        from apps.ticketing.services import inspect_ticket

        ticket, result = inspect_ticket(self.ticket.qr_token)

        self.assertEqual(result, CheckInLog.Result.ALLOWED)
        ticket.refresh_from_db()
        self.assertFalse(ticket.checked_in)
        self.assertEqual(CheckInLog.objects.count(), 0, 'inspection must not log or mutate')


@override_settings(REST_FRAMEWORK=NO_THROTTLE)
class RegistrationAPITests(APITestCase):
    def setUp(self):
        self.event = make_event()
        self.url = reverse('api-event-register', args=[self.event.slug])
        self.client.force_authenticate(make_attendee())

    def test_registration_requires_an_account(self):
        """
        Without email delivery the account is the only durable route back to a
        ticket, so an anonymous registration would be unreachable by its owner.
        """
        self.client.force_authenticate(None)
        response = self.client.post(self.url, VALID, format='json')

        self.assertEqual(response.status_code, 403)
        self.assertFalse(Registration.objects.exists(), 'nothing may be written')

    def test_registering_returns_the_ticket_reference(self):
        response = self.client.post(self.url, VALID, format='json')

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['payment']['kind'], 'none')
        self.assertIsNotNone(response.data['registration']['ticket_number'])

    def test_a_duplicate_registration_is_a_conflict_not_a_crash(self):
        self.client.post(self.url, VALID, format='json')

        response = self.client.post(self.url, VALID, format='json')

        self.assertEqual(response.status_code, 409)
        self.assertFalse(response.data['success'])
        self.assertEqual(response.data['code'], 'duplicate_email')

    def test_a_sold_out_event_is_a_conflict(self):
        Event.objects.filter(pk=self.event.pk).update(max_attendees=1)
        self.client.post(self.url, VALID, format='json')

        response = self.client.post(
            self.url,
            {**VALID, 'email': 'other@example.com', 'cnic': '35202-7654321-1'},
            format='json',
        )

        self.assertEqual(response.status_code, 409)
        self.assertIn('sold out', response.data['message'].lower())

    def test_a_malformed_email_is_a_validation_error(self):
        response = self.client.post(self.url, {**VALID, 'email': 'nope'}, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertIn('email', response.data['errors'])

    def test_the_response_never_echoes_the_cnic(self):
        response = self.client.post(self.url, VALID, format='json')

        body = response.content.decode()
        self.assertNotIn('35202', body)
        self.assertNotIn('1234567', body)

    def test_registration_status_is_readable_with_the_reference(self):
        created = self.client.post(self.url, VALID, format='json').data
        ref = created['registration']['public_ref']

        response = self.client.get(reverse('api-registration-status', args=[ref]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['full_name'], 'Ayesha Khan')

    def test_the_ticketing_summary_reports_remaining_seats(self):
        Event.objects.filter(pk=self.event.pk).update(max_attendees=50)
        self.client.post(self.url, VALID, format='json')

        response = self.client.get(reverse('api-event-ticketing', args=[self.event.slug]))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['registration_is_open'])
        self.assertEqual(response.data['seats_remaining'], 49)


@override_settings(REST_FRAMEWORK=NO_THROTTLE)
class TicketAccessTests(APITestCase):
    def setUp(self):
        self.event = make_event()
        self.registration, _, _ = register(self.event, **VALID)
        self.ticket = self.registration.ticket

    def test_the_attendee_reads_their_ticket_with_the_access_token(self):
        response = self.client.get(
            reverse('api-ticket-by-token', args=[self.ticket.access_token])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['ticket_number'], self.ticket.ticket_number)
        self.assertIn(str(self.ticket.qr_token), response.data['qr_payload'])

    def test_ticket_numbers_are_not_publicly_enumerable(self):
        """
        The PRD's GET /api/ticket/{ticket_number} would let anyone walk
        TEDX2026-0001, -0002, ... and harvest the attendee list.
        """
        response = self.client.get(f'/api/tickets/{self.ticket.ticket_number}/')

        self.assertIn(response.status_code, (401, 403))

    def test_an_unknown_access_token_is_a_404(self):
        response = self.client.get(
            reverse('api-ticket-by-token', args=['00000000-0000-0000-0000-000000000000'])
        )

        self.assertEqual(response.status_code, 404)


@override_settings(REST_FRAMEWORK=NO_THROTTLE)
class CheckInAPITests(APITestCase):
    def setUp(self):
        self.event = make_event()
        self.registration, _, _ = register(self.event, **VALID)
        self.ticket = self.registration.ticket
        self.volunteer = make_volunteer('scanner')

    def test_anonymous_users_cannot_check_anyone_in(self):
        response = self.client.post(
            reverse('api-checkin'), {'token': str(self.ticket.qr_token)}, format='json'
        )

        self.assertIn(response.status_code, (401, 403))
        self.ticket.refresh_from_db()
        self.assertFalse(self.ticket.checked_in)

    def test_a_logged_in_non_volunteer_cannot_check_anyone_in(self):
        get_user_model().objects.create_user(username='attendee', password='x' * 20)
        self.client.login(username='attendee', password='x' * 20)

        response = self.client.post(
            reverse('api-checkin'), {'token': str(self.ticket.qr_token)}, format='json'
        )

        self.assertEqual(response.status_code, 403)

    def test_a_volunteer_can_check_a_ticket_in(self):
        self.client.force_authenticate(self.volunteer)

        response = self.client.post(
            reverse('api-checkin'), {'token': str(self.ticket.qr_token)}, format='json'
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['allowed'])
        self.assertEqual(response.data['attendee_name'], 'Ayesha Khan')
        self.assertEqual(response.data['cnic_last4'], '5678')

    def test_a_second_scan_is_refused(self):
        self.client.force_authenticate(self.volunteer)
        self.client.post(reverse('api-checkin'), {'token': str(self.ticket.qr_token)}, format='json')

        response = self.client.post(
            reverse('api-checkin'), {'token': str(self.ticket.qr_token)}, format='json'
        )

        self.assertEqual(response.status_code, 409)
        self.assertFalse(response.data['allowed'])
        self.assertEqual(response.data['result'], CheckInLog.Result.DUPLICATE)

    def test_verify_shows_the_attendee_without_consuming_the_ticket(self):
        self.client.force_authenticate(self.volunteer)

        response = self.client.post(
            reverse('api-checkin-verify'), {'token': str(self.ticket.qr_token)}, format='json'
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['allowed'])
        self.ticket.refresh_from_db()
        self.assertFalse(self.ticket.checked_in)

    def test_a_get_request_can_never_check_anyone_in(self):
        """The QR encodes a URL, so a phone camera will GET it. That must be inert."""
        self.client.force_authenticate(self.volunteer)

        response = self.client.get(reverse('api-checkin'))

        self.assertEqual(response.status_code, 405)
        self.ticket.refresh_from_db()
        self.assertFalse(self.ticket.checked_in)

    def test_history_shows_only_this_volunteers_scans(self):
        other = make_volunteer('other-scanner')
        check_in(self.ticket.qr_token, volunteer=other)
        self.client.force_authenticate(self.volunteer)
        self.client.post(reverse('api-checkin'), {'token': 'garbage'}, format='json')

        response = self.client.get(reverse('api-checkin-history'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['result'], CheckInLog.Result.INVALID)

    def test_jwt_authenticates_the_scanner(self):
        token_response = self.client.post(
            reverse('token-obtain'),
            {'username': 'scanner', 'password': 'x' * 20},
            format='json',
        )
        self.assertEqual(token_response.status_code, 200)

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token_response.data["access"]}')
        response = self.client.post(
            reverse('api-checkin'), {'token': str(self.ticket.qr_token)}, format='json'
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['allowed'])


@override_settings(REST_FRAMEWORK=NO_THROTTLE)
class ClientCannotAssertPaymentTests(APITestCase):
    """Property 4: nothing a client sends may mark an order paid."""

    def setUp(self):
        self.event = make_event(title='Paid Event', ticket_price=Decimal('2500.00'))
        self.url = reverse('api-event-register', args=[self.event.slug])
        self.client.force_authenticate(make_attendee())

    def test_posting_a_paid_status_does_not_pay_the_order(self):
        response = self.client.post(
            self.url,
            {**VALID, 'status': 'confirmed', 'payment_status': 'paid', 'amount': '0.00'},
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        order = Order.objects.get()
        self.assertEqual(order.status, Order.Status.AWAITING_CONFIRMATION)
        self.assertEqual(order.amount, Decimal('2500.00'))
        self.assertFalse(Ticket.objects.exists())

    def test_orders_are_not_writable_through_the_api(self):
        self.client.post(self.url, VALID, format='json')
        order = Order.objects.get()
        staff = get_user_model().objects.create_superuser('boss', 'b@example.com', 'x' * 20)
        self.client.force_authenticate(staff)

        response = self.client.patch(
            f'/api/orders/{order.pk}/', {'status': 'paid'}, format='json'
        )

        self.assertEqual(response.status_code, 405)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.AWAITING_CONFIRMATION)

    def test_the_manual_provider_returns_transfer_instructions(self):
        response = self.client.post(self.url, VALID, format='json')

        payment = response.data['payment']
        self.assertEqual(payment['kind'], 'instructions')
        self.assertEqual(payment['details']['amount'], '2500.00')


@override_settings(REST_FRAMEWORK=NO_THROTTLE)
class OrganizerAccessTests(APITestCase):
    def setUp(self):
        self.event = make_event()
        register(self.event, **VALID)

    def test_registrations_are_not_publicly_listable(self):
        response = self.client.get('/api/registrations/')

        self.assertIn(response.status_code, (401, 403))

    def test_a_volunteer_cannot_read_the_registration_list(self):
        self.client.force_authenticate(make_volunteer('vol-only'))

        response = self.client.get('/api/registrations/')

        self.assertEqual(response.status_code, 403)

    def test_an_organizer_can_read_registrations(self):
        organizer = make_volunteer('boss-person', group=ORGANIZERS_GROUP)
        self.client.force_authenticate(organizer)

        response = self.client.get('/api/registrations/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)

    def test_the_organizer_list_shows_only_the_last_four_cnic_digits(self):
        self.client.force_authenticate(make_volunteer('boss2', group=ORGANIZERS_GROUP))

        body = self.client.get('/api/registrations/').content.decode()

        self.assertIn('5678', body)
        self.assertNotIn('35202', body)

    def test_the_organizer_ticket_list_never_exposes_scan_tokens(self):
        self.client.force_authenticate(make_volunteer('boss3', group=ORGANIZERS_GROUP))
        ticket = Ticket.objects.get()

        body = self.client.get('/api/tickets/').content.decode()

        self.assertIn(ticket.ticket_number, body)
        self.assertNotIn(str(ticket.qr_token), body)
        self.assertNotIn(str(ticket.access_token), body)


class EventTicketingFieldTests(TestCase):
    def test_a_free_event_is_flagged_free(self):
        self.assertTrue(make_event().is_free)
        self.assertFalse(make_event(title='Paid', ticket_price=Decimal('1.00')).is_free)

    def test_the_ticket_prefix_falls_back_to_the_event_year(self):
        event = make_event(start_datetime=datetime(2027, 3, 1, 10, tzinfo=dt_timezone.utc),
                           end_datetime=datetime(2027, 3, 1, 17, tzinfo=dt_timezone.utc))
        self.assertEqual(event.resolved_ticket_prefix, 'TEDX2027')

    def test_an_explicit_prefix_wins(self):
        event = make_event(ticket_prefix='TEDXUMT-SPECIAL')
        self.assertEqual(event.resolved_ticket_prefix, 'TEDXUMT-SPECIAL')

    def test_unlimited_capacity_reports_no_remaining_count(self):
        event = make_event(max_attendees=None)
        self.assertIsNone(event.seats_remaining())
        self.assertFalse(event.is_sold_out)

    def test_registration_close_must_follow_registration_open(self):
        from django.core.exceptions import ValidationError

        event = make_event(
            registration_opens_at=timezone.now() + timedelta(days=2),
            registration_closes_at=timezone.now() + timedelta(days=1),
        )
        with self.assertRaises(ValidationError):
            event.full_clean()
