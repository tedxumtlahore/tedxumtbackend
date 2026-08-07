"""
Stage 4 tests — organizer dashboard, analytics, and the attendee export.

The export is the sharp edge here: it takes personal data out of the system as
a file that ends up in someone's downloads folder. Its permissions and its
column list get more attention than the counts do.
"""

import csv
import io
from decimal import Decimal

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.common.permissions import ORGANIZERS_GROUP
from apps.ticketing.dashboard import EXPORT_COLUMNS
from apps.ticketing.models import Registration, Ticket
from apps.ticketing.services import check_in, mark_paid, register

from .tests import NO_THROTTLE, VALID, make_event, make_volunteer


def organizer(name='chief'):
    return make_volunteer(name, group=ORGANIZERS_GROUP)


@override_settings(REST_FRAMEWORK=NO_THROTTLE)
class DashboardPermissionTests(APITestCase):
    def setUp(self):
        self.event = make_event()

    def test_the_dashboard_is_not_public(self):
        response = self.client.get(reverse('api-dashboard'))

        self.assertIn(response.status_code, (401, 403))

    def test_a_volunteer_cannot_open_the_dashboard(self):
        """A volunteer scans tickets; they have no business seeing revenue."""
        self.client.force_authenticate(make_volunteer('door-staff'))

        response = self.client.get(reverse('api-dashboard'))

        self.assertEqual(response.status_code, 403)

    def test_analytics_and_export_are_organizer_only(self):
        self.client.force_authenticate(make_volunteer('door-staff-2'))

        self.assertEqual(self.client.get(reverse('api-analytics')).status_code, 403)
        self.assertEqual(self.client.get(reverse('api-registrations-export')).status_code, 403)

    def test_an_organizer_can_open_the_dashboard(self):
        self.client.force_authenticate(organizer())

        response = self.client.get(reverse('api-dashboard'))

        self.assertEqual(response.status_code, 200)


@override_settings(REST_FRAMEWORK=NO_THROTTLE)
class DashboardNumbersTests(APITestCase):
    def setUp(self):
        self.event = make_event(max_attendees=10)
        self.client.force_authenticate(organizer())

    def payload(self, **params):
        return self.client.get(reverse('api-dashboard'), params).data

    def test_an_empty_event_reports_zeroes(self):
        data = self.payload(event=self.event.slug)

        self.assertEqual(data['registrations']['total'], 0)
        self.assertEqual(data['door']['checked_in'], 0)
        self.assertEqual(data['door']['attendance_rate'], 0.0)
        self.assertEqual(data['capacity']['seats_remaining'], 10)

    def test_counts_follow_registrations_and_arrivals(self):
        first, _, _ = register(self.event, **VALID)
        register(self.event, full_name='Two', email='two@example.com', phone='03001234567')
        check_in(first.ticket.qr_token, volunteer=make_volunteer('scanner-1'))

        data = self.payload(event=self.event.slug)

        self.assertEqual(data['registrations']['total'], 2)
        self.assertEqual(data['registrations']['confirmed'], 2)
        self.assertEqual(data['door']['tickets_issued'], 2)
        self.assertEqual(data['door']['checked_in'], 1)
        self.assertEqual(data['door']['yet_to_arrive'], 1)
        self.assertEqual(data['door']['attendance_rate'], 50.0)
        self.assertEqual(data['capacity']['seats_taken'], 2)
        self.assertEqual(data['capacity']['percent_sold'], 20.0)

    def test_money_splits_collected_from_outstanding(self):
        event = make_event(title='Paid Event', ticket_price=Decimal('1500.00'))
        _, paid_order, _ = register(event, **VALID)
        register(event, full_name='Two', email='two@example.com', phone='03001234567')
        mark_paid(paid_order, reference='BANK-1')

        data = self.payload(event=event.slug)

        self.assertEqual(data['money']['collected'], '1500.00')
        self.assertEqual(data['money']['outstanding'], '1500.00')
        self.assertEqual(data['money']['currency'], 'PKR')

    def test_unlimited_capacity_reports_no_percentage(self):
        event = make_event(title='No Cap', max_attendees=None)

        data = self.payload(event=event.slug)

        self.assertIsNone(data['capacity']['percent_sold'])
        self.assertIsNone(data['capacity']['seats_remaining'])

    def test_recent_check_ins_lists_arrivals_only(self):
        first, _, _ = register(self.event, **VALID)
        volunteer = make_volunteer('scanner-2')
        check_in(first.ticket.qr_token, volunteer=volunteer)
        check_in('garbage-code', volunteer=volunteer)

        data = self.payload(event=self.event.slug)

        self.assertEqual(len(data['recent_check_ins']), 1)
        self.assertEqual(data['recent_check_ins'][0]['attendee_name'], 'Ayesha Khan')

    def test_it_defaults_to_the_soonest_upcoming_event(self):
        """On event day an organizer should not have to pick from a dropdown."""
        register(self.event, **VALID)

        data = self.payload()

        self.assertEqual(data['event']['slug'], self.event.slug)


@override_settings(REST_FRAMEWORK=NO_THROTTLE)
class AnalyticsTests(APITestCase):
    def setUp(self):
        self.event = make_event()
        self.client.force_authenticate(organizer('analyst'))

    def test_the_series_is_dense_and_cumulative(self):
        register(self.event, **VALID)

        data = self.client.get(reverse('api-analytics'), {'event': self.event.slug, 'days': 7}).data
        series = data['registrations_per_day']

        # Dense: every day in the window appears, including empty ones.
        self.assertEqual(len(series), 8)
        self.assertEqual(series[-1]['count'], 1)
        self.assertEqual(series[-1]['cumulative'], 1)
        self.assertEqual(series[0]['count'], 0)

    def test_the_window_is_clamped_to_something_sane(self):
        data = self.client.get(reverse('api-analytics'), {'days': '9999'}).data

        self.assertLessEqual(len(data['registrations_per_day']), 181)

    def test_a_junk_days_parameter_falls_back_to_the_default(self):
        data = self.client.get(reverse('api-analytics'), {'days': 'lots'}).data

        self.assertEqual(len(data['registrations_per_day']), 31)


@override_settings(REST_FRAMEWORK=NO_THROTTLE)
class ExportTests(APITestCase):
    def setUp(self):
        self.event = make_event()
        self.registration, _, _ = register(self.event, **VALID)
        self.client.force_authenticate(organizer('exporter'))

    def rows(self, **params):
        response = self.client.get(reverse('api-registrations-export'), params)
        body = response.content.decode('utf-8-sig')
        return response, list(csv.reader(io.StringIO(body)))

    def test_the_export_is_a_csv_attachment(self):
        response, rows = self.rows(event=self.event.slug)

        self.assertEqual(response.status_code, 200)
        self.assertIn('text/csv', response['Content-Type'])
        self.assertIn('attachment', response['Content-Disposition'])
        self.assertIn(self.event.slug, response['Content-Disposition'])
        self.assertEqual(rows[0], EXPORT_COLUMNS)

    def test_it_lists_each_attendee(self):
        _, rows = self.rows(event=self.event.slug)

        self.assertEqual(len(rows), 2)  # header + one attendee
        record = dict(zip(EXPORT_COLUMNS, rows[1]))
        self.assertEqual(record['full_name'], 'Ayesha Khan')
        self.assertEqual(record['email'], 'ayesha@example.com')
        self.assertEqual(record['ticket_number'], self.registration.ticket.ticket_number)
        self.assertEqual(record['checked_in'], 'no')

    def test_it_never_exports_the_cnic_hash_or_any_token(self):
        """
        A downloaded spreadsheet containing a scan token would be working door
        access sitting in someone's downloads folder.
        """
        response, _ = self.rows(event=self.event.slug)
        body = response.content.decode('utf-8-sig')
        ticket = self.registration.ticket

        self.assertNotIn(self.registration.cnic_hash, body)
        self.assertNotIn(str(ticket.qr_token), body)
        self.assertNotIn(str(ticket.access_token), body)
        self.assertNotIn(str(self.registration.public_ref), body)
        # The last four digits are there on purpose, for the door check.
        self.assertIn('5678', body)

    def test_the_column_list_is_an_explicit_allow_list(self):
        """Guards against a new model field silently joining the export."""
        for banned in ('cnic_hash', 'qr_token', 'access_token', 'public_ref'):
            self.assertNotIn(banned, EXPORT_COLUMNS)

    def test_arrival_shows_up_in_the_export(self):
        check_in(self.registration.ticket.qr_token, volunteer=make_volunteer('scanner-3'))

        _, rows = self.rows(event=self.event.slug)
        record = dict(zip(EXPORT_COLUMNS, rows[1]))

        self.assertEqual(record['checked_in'], 'yes')
        self.assertTrue(record['checked_in_at'])

    def test_the_export_is_not_public(self):
        self.client.force_authenticate(None)

        response = self.client.get(reverse('api-registrations-export'), {'event': self.event.slug})

        self.assertIn(response.status_code, (401, 403))
