"""
Stage 2 tests — QR rendering, PDF generation, and email delivery.

Kept separate from tests.py, which covers the correctness properties and the
API surface. Shared fixtures are imported rather than duplicated.
"""

from decimal import Decimal
from smtplib import SMTPException
from unittest import mock

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from apps.common.permissions import ORGANIZERS_GROUP
from apps.ticketing.models import Registration, Ticket
from apps.ticketing.rendering import QR_QUIET_ZONE, qr_png, ticket_pdf
from apps.ticketing.services import deliver_ticket, issue_ticket, mark_paid, register

from .tests import NO_THROTTLE, VALID, make_event, make_volunteer


class QRRenderingTests(TestCase):
    def test_qr_png_is_a_real_png(self):
        data = qr_png('https://example.com/checkin/abc')

        self.assertTrue(data.startswith(b'\x89PNG\r\n\x1a\n'))
        self.assertGreater(len(data), 100)

    def test_the_quiet_zone_meets_the_qr_specification(self):
        """
        Regression guard. A 2- or 3-module border was measured as undecodable
        by OpenCV's detector even at high resolution; the spec minimum is 4.
        Shipping less means finding out at the door on event day.
        """
        self.assertGreaterEqual(QR_QUIET_ZONE, 4)

    def test_the_default_border_is_the_quiet_zone(self):
        import inspect

        default = inspect.signature(qr_png).parameters['border'].default
        self.assertEqual(default, QR_QUIET_ZONE)


class TicketPDFTests(TestCase):
    def setUp(self):
        self.event = make_event()
        self.registration, _, _ = register(self.event, **VALID)
        self.ticket = self.registration.ticket

    def test_the_pdf_is_a_real_pdf(self):
        data = ticket_pdf(self.ticket, qr_payload='https://example.com/checkin/abc')

        self.assertTrue(data.startswith(b'%PDF-'))
        self.assertGreater(len(data), 2000)

    def test_the_pdf_renders_without_a_venue_address(self):
        """Venues are hand-edited, so the renderer must tolerate missing fields."""
        self.event.venue.address = ''
        self.event.venue.save()

        data = ticket_pdf(self.ticket, qr_payload='https://example.com/checkin/abc')

        self.assertTrue(data.startswith(b'%PDF-'))

    def test_the_pdf_renders_with_a_very_long_event_title(self):
        """The title is wrapped by hand; an overlong one must not blow the layout."""
        self.event.title = 'A ' + ('Very ' * 40) + 'Long Event Title'
        self.event.save()

        data = ticket_pdf(self.ticket, qr_payload='https://example.com/checkin/abc')

        self.assertTrue(data.startswith(b'%PDF-'))


class TicketEndpointTests(TestCase):
    def setUp(self):
        self.event = make_event()
        self.registration, _, _ = register(self.event, **VALID)
        self.ticket = self.registration.ticket

    def test_the_qr_endpoint_serves_a_private_png(self):
        response = self.client.get(reverse('api-ticket-qr', args=[self.ticket.access_token]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/png')
        # The image *is* the ticket — shared caches must not keep a copy.
        self.assertIn('private', response['Cache-Control'])

    def test_the_pdf_endpoint_serves_a_named_pdf(self):
        response = self.client.get(reverse('api-ticket-pdf', args=[self.ticket.access_token]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn(self.ticket.ticket_number, response['Content-Disposition'])

    def test_both_endpoints_reject_an_unknown_token(self):
        blank = '00000000-0000-0000-0000-000000000000'

        self.assertEqual(self.client.get(reverse('api-ticket-qr', args=[blank])).status_code, 404)
        self.assertEqual(self.client.get(reverse('api-ticket-pdf', args=[blank])).status_code, 404)

    def test_the_qr_encodes_the_scan_token_not_the_access_token(self):
        response = self.client.get(reverse('api-ticket-by-token', args=[self.ticket.access_token]))

        self.assertIn(str(self.ticket.qr_token), response.data['qr_payload'])
        self.assertNotIn(str(self.ticket.access_token), response.data['qr_payload'])


class TicketEmailTests(TestCase):
    """
    Delivery is scheduled with `transaction.on_commit`, which never fires under
    TestCase — each test runs in a transaction that is rolled back, so the
    commit hook is discarded. Every test here therefore drives the flow through
    `captureOnCommitCallbacks(execute=True)`.

    This matters beyond test plumbing: without it these tests pass whether or
    not any email is ever sent, which is exactly the kind of green suite that
    hides a broken feature.
    """

    def setUp(self):
        self.event = make_event()

    def register_and_deliver(self, event=None, **overrides):
        """Register, then run the on-commit hooks the way a real request would."""
        with self.captureOnCommitCallbacks(execute=True):
            return register(event or self.event, **{**VALID, **overrides})

    def test_issuing_a_ticket_emails_it_with_the_pdf_attached(self):
        registration, _, _ = self.register_and_deliver()

        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, ['ayesha@example.com'])
        self.assertIn(registration.ticket.ticket_number, message.subject)

        self.assertEqual(len(message.attachments), 1)
        name, content, mimetype = message.attachments[0]
        self.assertEqual(name, f'{registration.ticket.ticket_number}.pdf')
        self.assertEqual(mimetype, 'application/pdf')
        self.assertTrue(content.startswith(b'%PDF-'))

    def test_the_email_has_both_a_text_and_an_html_body(self):
        self.register_and_deliver()

        message = mail.outbox[0]
        self.assertIn('ticket', message.body.lower())
        html, mimetype = message.alternatives[0]
        self.assertEqual(mimetype, 'text/html')
        self.assertIn('TED', html)

    def test_the_email_never_contains_the_scan_token(self):
        """
        The QR lives in the attached PDF. Putting the raw scan token in the body
        would turn a forwarded email into working door access in plain text.
        """
        registration, _, _ = self.register_and_deliver()
        message = mail.outbox[0]
        body = message.body + message.alternatives[0][0]

        self.assertNotIn(str(registration.ticket.qr_token), body)
        self.assertIn(str(registration.ticket.access_token), body)

    def test_the_email_does_not_leak_the_cnic(self):
        self.register_and_deliver()
        message = mail.outbox[0]
        body = message.body + message.alternatives[0][0]

        self.assertNotIn('35202', body)

    def test_a_paid_event_sends_nothing_until_payment_is_confirmed(self):
        event = make_event(title='Paid Event', ticket_price=Decimal('1000.00'))

        registration, order, _ = self.register_and_deliver(event)
        self.assertEqual(len(mail.outbox), 0, 'no ticket, so nothing to send')

        with self.captureOnCommitCallbacks(execute=True):
            mark_paid(order, reference='BANK-1')

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(registration.event.title, mail.outbox[0].subject)

    def test_a_mail_failure_does_not_cost_the_attendee_their_ticket(self):
        """
        The ticket is the database row, not the email. A dead SMTP server must
        not roll back a confirmed registration.
        """
        with mock.patch(
            'apps.ticketing.emails.EmailMultiAlternatives.send',
            side_effect=SMTPException('smtp is down'),
        ):
            registration, _, _ = self.register_and_deliver()

        registration.refresh_from_db()
        self.assertEqual(registration.status, Registration.Status.CONFIRMED)
        self.assertTrue(Ticket.objects.filter(registration=registration).exists())
        self.assertEqual(len(mail.outbox), 0)

    def test_delivery_reports_failure_rather_than_raising(self):
        registration, _, _ = self.register_and_deliver()

        with mock.patch(
            'apps.ticketing.emails.EmailMultiAlternatives.send',
            side_effect=SMTPException('smtp is down'),
        ):
            sent = deliver_ticket(registration.ticket)

        self.assertFalse(sent)

    def test_resending_delivers_the_ticket_again(self):
        registration, _, _ = self.register_and_deliver()
        mail.outbox.clear()

        self.assertTrue(deliver_ticket(registration.ticket))
        self.assertEqual(len(mail.outbox), 1)

    def test_reissuing_an_existing_ticket_does_not_resend(self):
        registration, _, _ = self.register_and_deliver()
        mail.outbox.clear()

        with self.captureOnCommitCallbacks(execute=True):
            issue_ticket(registration)

        self.assertEqual(len(mail.outbox), 0, 'resending is an explicit action, not a side effect')


@override_settings(REST_FRAMEWORK=NO_THROTTLE)
class ResendEndpointTests(APITestCase):
    def setUp(self):
        self.event = make_event()
        self.registration, _, _ = register(self.event, **VALID)
        self.url = reverse('api-ticket-resend', args=[self.registration.ticket.ticket_number])
        mail.outbox.clear()

    def test_anonymous_users_cannot_resend_tickets(self):
        response = self.client.post(self.url)

        self.assertIn(response.status_code, (401, 403))
        self.assertEqual(len(mail.outbox), 0)

    def test_a_volunteer_cannot_resend_tickets(self):
        self.client.force_authenticate(make_volunteer('vol-resend'))

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 403)
        self.assertEqual(len(mail.outbox), 0)

    def test_an_organizer_can_resend_a_ticket(self):
        self.client.force_authenticate(make_volunteer('boss-resend', group=ORGANIZERS_GROUP))

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['success'])
        self.assertEqual(len(mail.outbox), 1)

    def test_resending_an_unknown_ticket_is_a_404(self):
        self.client.force_authenticate(make_volunteer('boss-404', group=ORGANIZERS_GROUP))

        response = self.client.post(reverse('api-ticket-resend', args=['TEDX9999-0001']))

        self.assertEqual(response.status_code, 404)
