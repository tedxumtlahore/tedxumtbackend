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

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.common.permissions import IsOrganizer, IsVolunteer
from apps.events.models import Event

from .models import CheckInLog, PaymentAccount, Registration, Ticket
from .serializers import (
    CheckInLogSerializer,
    CheckInRequestSerializer,
    PaymentAccountSerializer,
    PaymentProofSerializer,
    RegistrationCreateSerializer,
    RegistrationSerializer,
    TicketSerializer,
)
from .rendering import qr_png, ticket_pdf
from .services import (
    TicketingError,
    check_in,
    deliver_ticket,
    inspect_ticket,
    register,
    submit_payment_proof,
)
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
def payment_accounts_view(request):
    """
    GET /api/payment-accounts/ — where to send the money.

    Public: these are collection accounts, the same exposure as printing them
    on a poster. The attendee's own registration page reads this to show the
    numbers alongside their amount.
    """
    accounts = PaymentAccount.objects.filter(is_active=True, is_visible=True)
    return Response({'accounts': PaymentAccountSerializer(accounts, many=True).data})


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([RegistrationRateThrottle])
def payment_proof_view(request, public_ref):
    """
    POST /api/registrations/status/{public_ref}/payment-proof/ — "I've paid".

    Authorised by knowing the registration's unguessable reference, which only
    the attendee has. It records what they say and nothing more: the order stays
    unpaid until an organizer checks the statement and confirms. Nothing a
    client posts here can issue a ticket.
    """
    registration = get_object_or_404(
        Registration.objects.select_related('order', 'event'), public_ref=public_ref
    )

    serializer = PaymentProofSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
        submit_payment_proof(
            registration,
            reference=serializer.validated_data.get('reference', ''),
            paid_from_number=serializer.validated_data.get('paid_from_number', ''),
            proof=serializer.validated_data.get('proof'),
        )
    except TicketingError as exc:
        return Response(
            {'success': False, 'message': exc.message, 'code': exc.code, 'errors': {}},
            status=status.HTTP_409_CONFLICT,
        )

    registration.refresh_from_db()
    return Response({
        'success': True,
        'message': "Thanks — we'll confirm your payment and email your ticket, "
                   'usually within one working day.',
        'registration': RegistrationSerializer(registration, context={'request': request}).data,
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def ticket_qr_view(request, access_token):
    """
    GET /api/tickets/by-token/{access_token}/qr.png — the ticket's QR image.

    Rendered on demand rather than stored: the deploy target has an ephemeral
    filesystem, so a saved PNG would disappear and leave an attendee at the door
    with a broken image.
    """
    ticket = get_object_or_404(Ticket.objects.select_related('registration'), access_token=access_token)
    payload = request.build_absolute_uri(f'/checkin/{ticket.qr_token}')
    response = HttpResponse(qr_png(payload), content_type='image/png')
    # Private: this image is the ticket. Shared caches must not keep a copy.
    response['Cache-Control'] = 'private, max-age=300'
    return response


@api_view(['GET'])
@permission_classes([AllowAny])
def ticket_pdf_view(request, access_token):
    """GET /api/tickets/by-token/{access_token}/pdf/ — the printable ticket."""
    ticket = get_object_or_404(
        Ticket.objects.select_related(
            'registration', 'registration__event', 'registration__event__venue'
        ),
        access_token=access_token,
    )
    payload = request.build_absolute_uri(f'/checkin/{ticket.qr_token}')
    pdf_bytes = ticket_pdf(ticket, qr_payload=payload)

    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{ticket.ticket_number}.pdf"'
    response['Cache-Control'] = 'private, max-age=300'
    return response


@api_view(['POST'])
@permission_classes([IsOrganizer])
def resend_ticket_view(request, ticket_number):
    """
    POST /api/tickets/{ticket_number}/resend/ — email the ticket again.

    Delivery is best effort, so there has to be a deliberate way to retry when
    an attendee says the email never arrived.
    """
    ticket = get_object_or_404(
        Ticket.objects.select_related(
            'registration', 'registration__event', 'registration__event__venue'
        ),
        ticket_number=ticket_number,
    )
    sent = deliver_ticket(ticket, base_url=_public_base_url(request))

    return Response(
        {
            'success': sent,
            'message': (
                f'Ticket {ticket.ticket_number} re-sent to {ticket.registration.email}.'
                if sent else
                'The ticket could not be emailed. Check the mail settings and the server log.'
            ),
        },
        status=status.HTTP_200_OK if sent else status.HTTP_502_BAD_GATEWAY,
    )


def _public_base_url(request):
    """Prefer the configured public site URL; fall back to this request's host."""
    configured = getattr(settings, 'TICKET_BASE_URL', '')
    return configured or request.build_absolute_uri('/').rstrip('/')


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
