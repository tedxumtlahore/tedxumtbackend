"""
Ticketing API.

Endpoint permissions, at a glance:

| Endpoint                            | Who        |
|-------------------------------------|------------|
| POST /api/registrations/            | anyone     |
| GET  /api/registrations/{ref}/      | anyone with the ref (unguessable UUID) |
| GET  /api/tickets/by-token/{tok}/   | anyone with the token (unguessable UUID) |
| POST /api/checkin/verify/           | volunteers |
| POST /api/checkin/                  | volunteers |
| GET  /api/checkin/history/          | volunteers |
| GET  /api/registrations/list/       | organizers |
| GET  /api/tickets/                  | organizers |

Note there is no public endpoint keyed on `ticket_number`. Ticket numbers are
sequential by design, so a public lookup on them would let anyone enumerate the
full attendee list. Staff can still search by number through the admin.
"""

import logging

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.common.permissions import IsOrganizer, IsVolunteer
from apps.events.models import Event

from .models import CheckInLog, Registration, Ticket
from .serializers import (
    CheckInLogSerializer,
    CheckInRequestSerializer,
    RegistrationCreateSerializer,
    RegistrationSerializer,
    TicketSerializer,
)
from .services import TicketingError, check_in, inspect_ticket, register
from .throttling import CheckInRateThrottle, RegistrationRateThrottle

logger = logging.getLogger('apps.ticketing')

RESULT_MESSAGES = {
    CheckInLog.Result.ALLOWED: 'Checked in. Allow entry.',
    CheckInLog.Result.DUPLICATE: 'This ticket has already been used.',
    CheckInLog.Result.INVALID: 'Not a valid ticket.',
    CheckInLog.Result.UNPAID: 'This ticket has not been paid for.',
    CheckInLog.Result.WRONG_EVENT: 'This ticket is for a different event.',
    CheckInLog.Result.CANCELLED: 'This registration was cancelled.',
}


def _check_in_payload(ticket, result):
    """Shape a scan outcome for the volunteer's screen."""
    payload = {
        'result': result,
        'allowed': result == CheckInLog.Result.ALLOWED,
        'message': RESULT_MESSAGES.get(result, 'Unable to verify this ticket.'),
    }
    if ticket is not None:
        payload.update({
            'ticket_number': ticket.ticket_number,
            'attendee_name': ticket.registration.full_name,
            # Last four digits only — enough to match an ID card at the door.
            'cnic_last4': ticket.registration.cnic_last4,
            'event_title': ticket.registration.event.title,
            'checked_in_at': ticket.checked_in_at,
        })
    return payload


# ── Attendee ───────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([RegistrationRateThrottle])
def register_view(request, slug):
    """POST /api/events/{slug}/register/ — register for an event."""
    event = get_object_or_404(Event.objects.filter(is_active=True), slug=slug)

    serializer = RegistrationCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
        registration, order, instructions = register(event, **serializer.validated_data)
    except TicketingError as exc:
        # Business-rule rejections are 409s, not 400s — the input was well formed,
        # the world just says no (sold out, closed, already registered).
        return Response(
            {
                'success': False,
                'message': exc.message,
                'errors': {exc.field: [exc.message]} if exc.field else {},
                'code': exc.code,
                'status_code': status.HTTP_409_CONFLICT,
            },
            status=status.HTTP_409_CONFLICT,
        )

    return Response(
        {
            'success': True,
            'message': 'Registration received.',
            'registration': RegistrationSerializer(registration, context={'request': request}).data,
            'payment': instructions.as_dict(),
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(['GET'])
@permission_classes([AllowAny])
def registration_status_view(request, public_ref):
    """GET /api/registrations/{public_ref}/ — the attendee's own status page."""
    registration = get_object_or_404(
        Registration.objects.select_related('event', 'order', 'ticket'),
        public_ref=public_ref,
    )
    return Response(RegistrationSerializer(registration, context={'request': request}).data)


@api_view(['GET'])
@permission_classes([AllowAny])
def ticket_by_token_view(request, access_token):
    """GET /api/tickets/by-token/{access_token}/ — the attendee's ticket."""
    ticket = get_object_or_404(
        Ticket.objects.select_related(
            'registration', 'registration__event', 'registration__event__venue'
        ),
        access_token=access_token,
    )
    return Response(TicketSerializer(ticket, context={'request': request}).data)


@api_view(['GET'])
@permission_classes([AllowAny])
def event_ticketing_view(request, slug):
    """GET /api/events/{slug}/ticketing/ — is registration open, and at what price."""
    event = get_object_or_404(Event.objects.filter(is_active=True), slug=slug)
    return Response({
        'event': event.title,
        'slug': event.slug,
        'registration_is_open': event.registration_is_open,
        'closed_reason': event.registration_closed_reason(),
        'ticket_price': str(event.ticket_price),
        'currency': event.currency,
        'is_free': event.is_free,
        'capacity': event.max_attendees,
        'seats_remaining': event.seats_remaining(),
        'registration_opens_at': event.registration_opens_at,
        'registration_closes_at': event.registration_closes_at,
    })


# ── Volunteer check-in ─────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsVolunteer])
@throttle_classes([CheckInRateThrottle])
def check_in_verify_view(request):
    """
    POST /api/checkin/verify/ — look up a scanned code without consuming it.

    Lets the volunteer confirm the person in front of them matches the ticket
    before committing. Deliberately read-only: nothing here mutates a ticket.
    """
    serializer = CheckInRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    event = _event_from_slug(serializer.validated_data.get('event'))
    ticket, result = inspect_ticket(serializer.validated_data['token'], event=event)
    return Response(_check_in_payload(ticket, result))


@api_view(['POST'])
@permission_classes([IsVolunteer])
@throttle_classes([CheckInRateThrottle])
def check_in_view(request):
    """
    POST /api/checkin/ — verify and consume a ticket.

    POST-only and volunteer-only by design. The QR encodes a URL so a phone
    camera can open it, but opening that URL is a GET against the frontend and
    can never check anyone in — an attendee scanning their own ticket just
    lands on a login screen.
    """
    serializer = CheckInRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    event = _event_from_slug(serializer.validated_data.get('event'))
    ticket, result = check_in(
        serializer.validated_data['token'], volunteer=request.user, event=event
    )

    payload = _check_in_payload(ticket, result)
    http_status = status.HTTP_200_OK if payload['allowed'] else status.HTTP_409_CONFLICT
    return Response(payload, status=http_status)


@api_view(['GET'])
@permission_classes([IsVolunteer])
def check_in_history_view(request):
    """GET /api/checkin/history/ — this volunteer's recent scans."""
    logs = (
        CheckInLog.objects
        .select_related('ticket', 'ticket__registration', 'event', 'volunteer')
        .filter(volunteer=request.user)[:50]
    )
    return Response({'results': CheckInLogSerializer(logs, many=True).data})


def _event_from_slug(slug):
    """Optional event scoping so a scanner at one door rejects other events' tickets."""
    if not slug:
        return None
    return Event.objects.filter(slug=slug).first()
