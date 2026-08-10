"""
Tests for the manual payment flow: where to send money, and telling us you sent it.

The property that matters most here is that submitting proof is *not* paying.
An attendee can claim anything; only an organizer checking the statement moves
an order to paid.
"""

import shutil
import tempfile
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from apps.ticketing.models import Order, PaymentAccount, Registration, Ticket
from apps.ticketing.services import TicketingError, mark_paid, register, submit_payment_proof

from apps.common.permissions import ORGANIZERS_GROUP

from .tests import NO_THROTTLE, VALID, make_event, make_volunteer

TINY_GIF = (
    b'GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!'
    b'\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
)

# Uploads in tests are real file writes; without this they accumulate in the
# project's media/ directory forever.
TEMP_MEDIA_ROOT = tempfile.mkdtemp(prefix='tedxumt-payment-test-')


class MediaIsolated:
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)


def screenshot(name='payment.gif'):
    return SimpleUploadedFile(name, TINY_GIF, content_type='image/gif')


def make_account(**overrides):
    defaults = {
        'provider': PaymentAccount.ProviderChoices.EASYPAISA,
        'account_title': 'TEDxUMT Lahore',
        'account_number': '03001234567',
        'order': 0,
    }
    defaults.update(overrides)
    return PaymentAccount.objects.create(**defaults)


class PaymentAccountTests(TestCase):
    def test_accounts_order_by_rank(self):
        make_account(provider=PaymentAccount.ProviderChoices.JAZZCASH,
                     account_number='03119999999', order=1)
        make_account(order=0)

        self.assertEqual(
            [a.provider for a in PaymentAccount.objects.all()],
            ['easypaisa', 'jazzcash'],
        )

    def test_str_names_the_provider_and_number(self):
        self.assertEqual(str(make_account()), 'Easypaisa — 03001234567')


@override_settings(REST_FRAMEWORK=NO_THROTTLE)
class PaymentAccountAPITests(APITestCase):
    def test_accounts_are_publicly_readable(self):
        make_account()

        response = self.client.get(reverse('api-payment-accounts'))

        self.assertEqual(response.status_code, 200)
        account = response.data['accounts'][0]
        self.assertEqual(account['account_number'], '03001234567')
        self.assertEqual(account['provider_label'], 'Easypaisa')

    def test_hidden_accounts_are_not_listed(self):
        make_account(is_visible=False)

        response = self.client.get(reverse('api-payment-accounts'))

        self.assertEqual(response.data['accounts'], [])

    def test_registration_instructions_include_the_accounts(self):
        """
        The instructions used to say "use the details below" and then show only
        an amount — there was nowhere to configure a number to pay to.
        """
        make_account()
        event = make_event(title='Paid Event', ticket_price=Decimal('1500.00'))

        response = self.client.post(
            reverse('api-event-register', args=[event.slug]), VALID, format='json'
        )

        details = response.data['payment']['details']
        self.assertEqual(len(details['accounts']), 1)
        self.assertEqual(details['accounts'][0]['account_number'], '03001234567')
        self.assertEqual(details['amount'], '1500.00')


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PaymentProofServiceTests(MediaIsolated, TestCase):
    def setUp(self):
        self.event = make_event(title='Paid Event', ticket_price=Decimal('1500.00'))
        self.registration, self.order, _ = register(self.event, **VALID)

    def test_submitting_proof_records_it_without_paying(self):
        """The whole point: a claim is not a payment."""
        submit_payment_proof(
            self.registration, reference='TXN-8891', paid_from_number='03007654321'
        )

        self.order.refresh_from_db()
        self.assertEqual(self.order.reference, 'TXN-8891')
        self.assertEqual(self.order.paid_from_number, '03007654321')
        self.assertIsNotNone(self.order.proof_submitted_at)
        self.assertEqual(self.order.status, Order.Status.AWAITING_CONFIRMATION)
        self.assertFalse(Ticket.objects.filter(registration=self.registration).exists())

    def test_an_organizer_confirming_afterwards_issues_the_ticket(self):
        submit_payment_proof(self.registration, reference='TXN-8891')

        ticket = mark_paid(self.order, confirmed_by=make_volunteer('boss-confirm'))

        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.PAID)
        # The attendee's reference survives the confirmation.
        self.assertEqual(self.order.reference, 'TXN-8891')
        self.assertTrue(ticket.ticket_number)

    def test_proof_cannot_be_resubmitted_after_confirmation(self):
        mark_paid(self.order, reference='BANK-1')

        with self.assertRaises(TicketingError) as ctx:
            submit_payment_proof(self.registration, reference='TXN-LATE')

        self.assertEqual(ctx.exception.code, 'already_paid')

    def test_a_cancelled_order_refuses_proof(self):
        Order.objects.filter(pk=self.order.pk).update(status=Order.Status.CANCELLED)
        self.order.refresh_from_db()

        with self.assertRaises(TicketingError) as ctx:
            submit_payment_proof(self.registration, reference='TXN-1')

        self.assertEqual(ctx.exception.code, 'order_closed')

    def test_resubmitting_overwrites_a_typo(self):
        submit_payment_proof(self.registration, reference='TXN-WRONG')
        submit_payment_proof(self.registration, reference='TXN-RIGHT')

        self.order.refresh_from_db()
        self.assertEqual(self.order.reference, 'TXN-RIGHT')


@override_settings(REST_FRAMEWORK=NO_THROTTLE, MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PaymentProofAPITests(MediaIsolated, APITestCase):
    def setUp(self):
        make_account()
        self.event = make_event(title='Paid Event', ticket_price=Decimal('1500.00'))
        self.registration, self.order, _ = register(self.event, **VALID)
        self.url = reverse('api-payment-proof', args=[self.registration.public_ref])

    def test_the_attendee_can_report_their_transfer(self):
        response = self.client.post(
            self.url, {'reference': 'TXN-4410', 'paid_from_number': '03009998888'}, format='json'
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['success'])
        self.assertTrue(response.data['registration']['proof_submitted'])
        self.order.refresh_from_db()
        self.assertEqual(self.order.reference, 'TXN-4410')

    def test_a_screenshot_can_be_attached(self):
        response = self.client.post(
            self.url, {'reference': 'TXN-1', 'proof': screenshot()}, format='multipart'
        )

        self.assertEqual(response.status_code, 200)
        self.order.refresh_from_db()
        self.assertTrue(self.order.payment_proof)
        # Randomised filename: a predictable one would be a guessable URL to an
        # image showing the sender's balance.
        self.assertNotIn('payment.gif', self.order.payment_proof.name)
        self.assertTrue(self.order.payment_proof.name.startswith('payments/proofs/'))

    def test_an_empty_submission_is_rejected(self):
        response = self.client.post(self.url, {}, format='json')

        self.assertEqual(response.status_code, 400)

    def test_submitting_proof_never_issues_a_ticket(self):
        self.client.post(self.url, {'reference': 'TXN-FAKE'}, format='json')

        self.assertFalse(Ticket.objects.exists())
        self.order.refresh_from_db()
        self.assertNotEqual(self.order.status, Order.Status.PAID)

    def test_the_response_never_exposes_the_screenshot_url(self):
        self.client.post(self.url, {'reference': 'T', 'proof': screenshot()}, format='multipart')

        response = self.client.get(
            reverse('api-registration-status', args=[self.registration.public_ref])
        )

        self.assertNotIn('payments/proofs', response.content.decode())

    def test_an_unknown_reference_is_a_404(self):
        response = self.client.post(
            reverse('api-payment-proof', args=['00000000-0000-0000-0000-000000000000']),
            {'reference': 'TXN-1'}, format='json',
        )

        self.assertEqual(response.status_code, 404)

    def test_reporting_after_confirmation_is_a_conflict(self):
        mark_paid(self.order, reference='BANK-1')

        response = self.client.post(self.url, {'reference': 'TXN-LATE'}, format='json')

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data['code'], 'already_paid')

    def test_the_status_page_shows_whether_proof_was_sent(self):
        status_url = reverse('api-registration-status', args=[self.registration.public_ref])

        before = self.client.get(status_url).data
        self.client.post(self.url, {'reference': 'TXN-9'}, format='json')
        after = self.client.get(status_url).data

        self.assertFalse(before['proof_submitted'])
        self.assertTrue(after['proof_submitted'])
        self.assertEqual(after['payment_reference'], 'TXN-9')


@override_settings(REST_FRAMEWORK=NO_THROTTLE)
class OrderCollectionTests(APITestCase):
    """
    The organizer-facing order list.

    This existed untested and returned a 500: `has_proof` was declared as a
    SerializerMethodField with no matching method. Serializing anything through
    it raised, so the endpoint was broken for every caller who was allowed to
    use it — found by probing the authorization matrix rather than by the suite.
    """

    def setUp(self):
        self.event = make_event(title='Paid Event', ticket_price=Decimal('1500.00'))
        self.registration, self.order, _ = register(self.event, **VALID)
        self.client.force_authenticate(make_volunteer('order-reader', group=ORGANIZERS_GROUP))

    def test_an_organizer_can_list_orders(self):
        response = self.client.get('/api/orders/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)

    def test_the_row_reports_whether_proof_was_submitted(self):
        before = self.client.get('/api/orders/').data['results'][0]
        self.assertFalse(before['has_proof'])

        submit_payment_proof(self.registration, reference='TXN-1', paid_from_number='03001112222')

        after = self.client.get('/api/orders/').data['results'][0]
        self.assertTrue(after['has_proof'])
        self.assertEqual(after['paid_from_number'], '03001112222')

    def test_orders_are_read_only_through_the_api(self):
        response = self.client.patch(f'/api/orders/{self.order.pk}/', {'status': 'paid'}, format='json')

        self.assertEqual(response.status_code, 405)
        self.order.refresh_from_db()
        self.assertNotEqual(self.order.status, Order.Status.PAID)

    def test_a_volunteer_cannot_list_orders(self):
        self.client.force_authenticate(make_volunteer('not-an-organizer'))

        self.assertEqual(self.client.get('/api/orders/').status_code, 403)


class RegistrationThrottleTests(APITestCase):
    """
    The registration throttle is the only thing stopping a script from taking
    every seat. It was wired but untested — a live probe could not tell a
    working throttle from a missing one, because development allows 200/hour.

    DRF reads DEFAULT_THROTTLE_RATES into a class attribute at import time, so
    override_settings cannot reach it; the rate is patched on the class.
    """

    def setUp(self):
        from rest_framework.throttling import SimpleRateThrottle

        self.original = dict(SimpleRateThrottle.THROTTLE_RATES)
        SimpleRateThrottle.THROTTLE_RATES = {**self.original, 'registration': '3/hour'}
        SimpleRateThrottle.cache.clear()
        self.event = make_event(max_attendees=None)

    def tearDown(self):
        from rest_framework.throttling import SimpleRateThrottle

        SimpleRateThrottle.THROTTLE_RATES = self.original
        SimpleRateThrottle.cache.clear()

    def register_once(self, n):
        return self.client.post(
            reverse('api-event-register', args=[self.event.slug]),
            {'full_name': f'Bulk {n}', 'email': f'bulk{n}@example.com', 'phone': '03001234567'},
            format='json',
        )

    def test_a_flood_of_registrations_is_cut_off(self):
        codes = [self.register_once(n).status_code for n in range(5)]

        self.assertEqual(codes[:3], [201, 201, 201])
        self.assertIn(429, codes, 'the throttle must engage — otherwise a script can take every seat')

    def test_the_throttle_does_not_consume_capacity(self):
        """A rejected request must not hold a seat."""
        for n in range(5):
            self.register_once(n)

        self.assertEqual(Registration.objects.filter(event=self.event).count(), 3)
