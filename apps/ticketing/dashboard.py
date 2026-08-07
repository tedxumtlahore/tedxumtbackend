"""
Organizer dashboard: live counts, a short time series, and the attendee export.

Everything here is organizer-only. The numbers are computed with aggregates
rather than by walking querysets — at a hundred tickets either would be fine,
but the door view is polled every few seconds on event day and there is no
reason to make the database do more work than one row of counts.
"""

import csv
from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncDate
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from apps.common.permissions import IsOrganizer
from apps.events.models import Event

from .models import CheckInLog, Order, Registration, Ticket
from .serializers import CheckInLogSerializer


def _money(value):
    """
    Format an aggregate as a currency string.

    `Sum()` over a DecimalField comes back without the field's scale on SQLite,
    so a total renders as "1500" next to a price of "1500.00". Quantizing keeps
    every amount on the dashboard formatted the same way.
    """
    return str((value or Decimal('0')).quantize(Decimal('0.01')))


def _resolve_event(request):
    """
    The event the dashboard is about.

    Defaults to the soonest upcoming event, because on event day that is the
    one an organizer means — asking them to pick from a dropdown first would be
    friction at exactly the wrong moment.
    """
    slug = request.query_params.get('event')
    if slug:
        return get_object_or_404(Event, slug=slug)

    upcoming = (
        Event.objects.filter(is_active=True, start_datetime__gte=timezone.now())
        .order_by('start_datetime')
        .first()
    )
    return upcoming or Event.objects.filter(is_active=True).order_by('-start_datetime').first()


@api_view(['GET'])
@permission_classes([IsOrganizer])
def dashboard_view(request):
    """GET /api/dashboard/?event=<slug> — the numbers an organizer watches."""
    event = _resolve_event(request)
    if event is None:
        return Response({'event': None, 'message': 'No events exist yet.'})

    registrations = Registration.objects.filter(event=event)
    by_status = dict(
        registrations.values_list('status').annotate(n=Count('id')).values_list('status', 'n')
    )

    tickets = Ticket.objects.filter(registration__event=event)
    issued = tickets.count()
    checked_in = tickets.filter(checked_in=True).count()

    orders = Order.objects.filter(registration__event=event)
    money = orders.aggregate(
        collected=Sum('amount', filter=Q(status=Order.Status.PAID)),
        outstanding=Sum('amount', filter=Q(status__in=[
            Order.Status.PENDING, Order.Status.AWAITING_CONFIRMATION,
        ])),
    )

    seats_taken = event.seats_taken()
    recent = (
        CheckInLog.objects.filter(event=event, result=CheckInLog.Result.ALLOWED)
        .select_related('ticket', 'ticket__registration', 'volunteer', 'event')[:10]
    )

    return Response({
        'event': {
            'title': event.title,
            'slug': event.slug,
            'start_datetime': event.start_datetime,
            'status': event.status,
            'registration_is_open': event.registration_is_open,
            'closed_reason': event.registration_closed_reason(),
        },
        'capacity': {
            'capacity': event.max_attendees,
            'seats_taken': seats_taken,
            'seats_remaining': event.seats_remaining(),
            # None when capacity is unlimited — the UI shows a count, not a bar.
            'percent_sold': (
                round(seats_taken / event.max_attendees * 100, 1)
                if event.max_attendees else None
            ),
        },
        'registrations': {
            'total': registrations.count(),
            'confirmed': by_status.get(Registration.Status.CONFIRMED, 0),
            'pending': by_status.get(Registration.Status.PENDING, 0),
            'cancelled': by_status.get(Registration.Status.CANCELLED, 0),
            'expired': by_status.get(Registration.Status.EXPIRED, 0),
        },
        'door': {
            'tickets_issued': issued,
            'checked_in': checked_in,
            'yet_to_arrive': max(0, issued - checked_in),
            'attendance_rate': round(checked_in / issued * 100, 1) if issued else 0.0,
        },
        'money': {
            'currency': event.currency,
            'ticket_price': str(event.ticket_price),
            'collected': _money(money['collected']),
            'outstanding': _money(money['outstanding']),
        },
        'recent_check_ins': CheckInLogSerializer(recent, many=True).data,
        'generated_at': timezone.now(),
    })


@api_view(['GET'])
@permission_classes([IsOrganizer])
def analytics_view(request):
    """
    GET /api/analytics/?event=<slug>&days=30 — registrations and arrivals over time.

    Returns a dense series (days with no registrations appear as zeros) so the
    frontend can render it without having to fill gaps itself.
    """
    event = _resolve_event(request)
    if event is None:
        return Response({'event': None, 'registrations_per_day': [], 'check_ins_per_hour': []})

    try:
        days = max(1, min(int(request.query_params.get('days', 30)), 180))
    except (TypeError, ValueError):
        days = 30

    since = timezone.now() - timedelta(days=days)

    counts = dict(
        Registration.objects.filter(event=event, created_at__gte=since)
        .annotate(day=TruncDate('created_at'))
        .values_list('day')
        .annotate(n=Count('id'))
        .values_list('day', 'n')
    )

    today = timezone.localdate()
    series, running = [], 0
    for offset in range(days, -1, -1):
        day = today - timedelta(days=offset)
        n = counts.get(day, 0)
        running += n
        series.append({'date': day.isoformat(), 'count': n, 'cumulative': running})

    # Arrivals bunch into the hour around doors opening — useful for staffing.
    check_ins = (
        Ticket.objects.filter(registration__event=event, checked_in=True)
        .annotate(day=TruncDate('checked_in_at'))
        .values_list('day')
        .annotate(n=Count('id'))
        .order_by('day')
    )

    return Response({
        'event': {'title': event.title, 'slug': event.slug},
        'registrations_per_day': series,
        'check_ins_per_day': [
            {'date': day.isoformat() if day else None, 'count': n} for day, n in check_ins
        ],
    })


#: Columns in the attendee export. Deliberately excludes `cnic_hash`,
#: `qr_token`, and `access_token`: the hash is useless to a human and the
#: tokens would turn a downloaded spreadsheet into working door access.
EXPORT_COLUMNS = [
    'ticket_number', 'full_name', 'email', 'phone', 'cnic_last4',
    'university', 'occupation', 'status', 'payment_status', 'amount',
    'checked_in', 'checked_in_at', 'registered_at',
]


@api_view(['GET'])
@permission_classes([IsOrganizer])
def export_registrations_view(request):
    """
    GET /api/registrations/export/?event=<slug> — the attendee list as CSV.

    This file is personal data leaving the system: names, emails, and phone
    numbers for every attendee. It is organizer-only, and the columns are an
    explicit allow-list so a future field cannot silently end up in a
    spreadsheet in someone's downloads folder.
    """
    event = _resolve_event(request)
    if event is None:
        return Response({'detail': 'No events exist yet.'}, status=404)

    registrations = (
        Registration.objects.filter(event=event)
        .select_related('order', 'ticket')
        .order_by('created_at')
    )

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    filename = f'{event.slug}-attendees-{timezone.localdate().isoformat()}.csv'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    # Excel needs the BOM to read UTF-8 names correctly.
    response.write('﻿')

    writer = csv.writer(response)
    writer.writerow(EXPORT_COLUMNS)

    for registration in registrations:
        ticket = getattr(registration, 'ticket', None)
        order = getattr(registration, 'order', None)
        writer.writerow([
            ticket.ticket_number if ticket else '',
            registration.full_name,
            registration.email,
            registration.phone,
            registration.cnic_last4,
            registration.university,
            registration.occupation,
            registration.get_status_display(),
            order.get_status_display() if order else '',
            order.amount if order else '',
            'yes' if ticket and ticket.checked_in else 'no',
            timezone.localtime(ticket.checked_in_at).isoformat()
            if ticket and ticket.checked_in_at else '',
            timezone.localtime(registration.created_at).isoformat(),
        ])

    return response
