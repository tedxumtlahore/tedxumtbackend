"""
Ticketing business logic.

Everything that has to be *correct under concurrency* lives here rather than in
a serializer or a view, so there is exactly one place to audit:

- `register`      — capacity is checked under a row lock, so the event cannot oversell
- `issue_ticket`  — ticket numbers come from a locked counter, so they cannot collide
- `mark_paid`     — the only path that creates a ticket
- `check_in`      — a single conditional UPDATE, so a ticket cannot be used twice

Views call these; they never manipulate the models directly.
"""

import logging
import uuid
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.events.models import Event

from .models import CheckInLog, Order, Registration, Ticket, TicketSequence, hash_identifier
from .providers import provider_for_event

logger = logging.getLogger('apps.ticketing')


class TicketingError(Exception):
    """Business-rule failure with a message safe to show the attendee."""

    def __init__(self, message, code='error', field=None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.field = field


# ── Registration ───────────────────────────────────────────────────────────

def _release_expired_holds(event):
    """Free seats held by pending registrations whose window has passed."""
    if not event.registration_hold_minutes:
        return 0
    return Registration.objects.filter(
        event=event,
        status=Registration.Status.PENDING,
        hold_expires_at__isnull=False,
        hold_expires_at__lt=timezone.now(),
    ).update(status=Registration.Status.EXPIRED)


@transaction.atomic
def register(event, *, full_name, email, phone, cnic='', university='', occupation=''):
    """
    Create a registration and its order.

    The whole thing runs inside one transaction with the event row locked, so
    two people racing for the last seat cannot both succeed. Note that SQLite
    has no row-level locking — `select_for_update` is a no-op there and the
    guarantee rests on SQLite's database-wide write lock instead. On PostgreSQL
    this is a genuine `SELECT ... FOR UPDATE`.
    """
    locked_event = Event.objects.select_for_update().get(pk=event.pk)

    _release_expired_holds(locked_event)

    closed_reason = locked_event.registration_closed_reason()
    if closed_reason:
        raise TicketingError(closed_reason, code='registration_closed')

    email = (email or '').strip().lower()
    cnic_hash, cnic_last4 = hash_identifier(cnic)

    seat_holders = Registration.objects.holding_seats(locked_event)
    if seat_holders.filter(email=email).exists():
        raise TicketingError(
            'This email address is already registered for this event.',
            code='duplicate_email',
            field='email',
        )
    if cnic_hash and seat_holders.filter(cnic_hash=cnic_hash).exists():
        raise TicketingError(
            'This CNIC / passport number is already registered for this event.',
            code='duplicate_cnic',
            field='cnic',
        )

    hold_expires_at = None
    if locked_event.registration_hold_minutes:
        hold_expires_at = timezone.now() + timedelta(minutes=locked_event.registration_hold_minutes)

    registration = Registration(
        event=locked_event,
        full_name=(full_name or '').strip(),
        email=email,
        phone=(phone or '').strip(),
        university=(university or '').strip(),
        occupation=(occupation or '').strip(),
        hold_expires_at=hold_expires_at,
    )
    registration.cnic_hash = cnic_hash
    registration.cnic_last4 = cnic_last4
    registration.save()

    provider = provider_for_event(locked_event)
    order = Order.objects.create(
        registration=registration,
        provider=provider.key,
        amount=locked_event.ticket_price,
        currency=locked_event.currency,
        status=Order.Status.PENDING,
    )

    if provider.settles_immediately:
        mark_paid(order, reference='free')
    else:
        order.status = Order.Status.AWAITING_CONFIRMATION
        order.save(update_fields=['status', 'updated_at'])

    instructions = provider.start(order)
    registration.refresh_from_db()
    return registration, order, instructions


# ── Payment ────────────────────────────────────────────────────────────────

@transaction.atomic
def mark_paid(order, *, reference='', confirmed_by=None, payload=None):
    """
    Settle an order and issue its ticket. The only path that creates a Ticket.

    Idempotent: confirming an already-paid order returns the existing ticket
    rather than issuing a second one, so a double-clicked admin action or a
    replayed webhook cannot mint duplicates.
    """
    locked_order = Order.objects.select_for_update().get(pk=order.pk)

    if locked_order.status == Order.Status.PAID:
        return Ticket.objects.filter(registration=locked_order.registration).first()

    if locked_order.status in {Order.Status.CANCELLED, Order.Status.REFUNDED}:
        raise TicketingError(
            'This order can no longer be paid.', code='order_not_payable'
        )

    locked_order.status = Order.Status.PAID
    locked_order.paid_at = timezone.now()
    if reference:
        locked_order.reference = reference
    if confirmed_by is not None:
        locked_order.confirmed_by = confirmed_by
    if payload:
        locked_order.raw_payload = payload
    locked_order.save()

    registration = locked_order.registration
    registration.status = Registration.Status.CONFIRMED
    registration.hold_expires_at = None
    registration.save(update_fields=['status', 'hold_expires_at', 'updated_at'])

    ticket = issue_ticket(registration)
    logger.info('Ticket %s issued for order %s', ticket.ticket_number, locked_order.pk)
    return ticket


def mark_failed(order, *, reason='', payload=None):
    order.status = Order.Status.FAILED
    if reason:
        order.reference = reason[:120]
    if payload:
        order.raw_payload = payload
    order.save()
    return order


# ── Tickets ────────────────────────────────────────────────────────────────

def _ensure_sequence(event):
    """
    Get or create the event's counter, allocating a globally unique prefix.

    The default prefix is derived from the year, so a second event in the same
    year would otherwise reuse TEDX2026 and collide on ticket numbers. Suffixes
    are appended until the prefix is free.
    """
    sequence = TicketSequence.objects.filter(event=event).first()
    if sequence is not None:
        return sequence

    base = event.resolved_ticket_prefix
    for attempt in range(1, 100):
        candidate = base if attempt == 1 else f'{base}-{attempt}'
        if TicketSequence.objects.filter(prefix=candidate).exists():
            continue
        try:
            return TicketSequence.objects.create(event=event, prefix=candidate)
        except IntegrityError:
            # Another request claimed this prefix (or this event's row) first.
            existing = TicketSequence.objects.filter(event=event).first()
            if existing is not None:
                return existing

    raise TicketingError(
        'Could not allocate a ticket number prefix for this event.',
        code='prefix_exhausted',
    )


def next_ticket_number(event):
    """
    Reserve the next number for `event`, e.g. TEDX2026-0001.

    The counter row is locked for the duration, so concurrent issuance produces
    a gapless sequence with no duplicates.
    """
    sequence = _ensure_sequence(event)
    locked = TicketSequence.objects.select_for_update().get(pk=sequence.pk)
    locked.last_number += 1
    locked.save(update_fields=['last_number'])
    return f'{locked.prefix}-{locked.last_number:04d}'


@transaction.atomic
def issue_ticket(registration):
    """Issue the ticket for a confirmed registration, or return the existing one."""
    existing = Ticket.objects.filter(registration=registration).first()
    if existing is not None:
        return existing

    if not getattr(registration, 'order', None) or not registration.order.is_paid:
        raise TicketingError(
            'A ticket cannot be issued before the order is paid.', code='not_paid'
        )

    return Ticket.objects.create(
        registration=registration,
        ticket_number=next_ticket_number(registration.event),
    )


# ── Check-in ───────────────────────────────────────────────────────────────

def _log(result, *, ticket=None, event=None, volunteer=None, token=''):
    return CheckInLog.objects.create(
        ticket=ticket,
        event=event or (ticket.registration.event if ticket else None),
        volunteer=volunteer if (volunteer and volunteer.is_authenticated) else None,
        scanned_token=str(token)[:100],
        result=result,
    )


def _find_ticket(token):
    """
    Resolve a scanned QR payload to a ticket, tolerating a full check-in URL.

    The token is parsed as a UUID *before* it reaches the ORM. Handing a
    non-UUID string to a UUIDField lookup raises ValidationError from deep
    inside Django, which would surface as a 500 — and a volunteer scanning a
    bus ticket by mistake must get "invalid ticket", not a server error.
    """
    raw = str(token or '').strip()
    if not raw:
        return None

    # Scanners submit either the bare token or the whole URL the QR encodes.
    candidate = raw.rstrip('/').rsplit('/', 1)[-1]
    try:
        parsed = uuid.UUID(candidate)
    except (ValueError, AttributeError, TypeError):
        return None

    return (
        Ticket.objects
        .select_related('registration', 'registration__event', 'registration__order')
        .filter(qr_token=parsed)
        .first()
    )


def inspect_ticket(token, *, event=None):
    """
    Read-only verification. Returns `(ticket, result)` and changes nothing.

    Lets the scanner show the attendee's details for confirmation before a
    volunteer commits the check-in.
    """
    ticket = _find_ticket(token)
    if ticket is None:
        return None, CheckInLog.Result.INVALID

    registration = ticket.registration
    if event is not None and registration.event_id != event.pk:
        return ticket, CheckInLog.Result.WRONG_EVENT
    if registration.status == Registration.Status.CANCELLED:
        return ticket, CheckInLog.Result.CANCELLED
    if not getattr(registration, 'order', None) or not registration.order.is_paid:
        return ticket, CheckInLog.Result.UNPAID
    if ticket.checked_in:
        return ticket, CheckInLog.Result.DUPLICATE
    return ticket, CheckInLog.Result.ALLOWED


def check_in(token, *, volunteer, event=None):
    """
    Verify and check a ticket in. Every attempt is logged, including failures.

    The state change is a single conditional UPDATE rather than a read followed
    by a save: if two volunteers scan the same QR at the same instant, exactly
    one `update()` matches a row and the other is told the ticket is already
    used. A read-then-write would let both through.
    """
    ticket, result = inspect_ticket(token, event=event)

    if result != CheckInLog.Result.ALLOWED:
        _log(result, ticket=ticket, event=event, volunteer=volunteer, token=token)
        return ticket, result

    now = timezone.now()
    updated = Ticket.objects.filter(pk=ticket.pk, checked_in=False).update(
        checked_in=True, checked_in_at=now, checked_in_by=volunteer
    )
    if not updated:
        # Lost the race — another scanner got there first.
        _log(CheckInLog.Result.DUPLICATE, ticket=ticket, volunteer=volunteer, token=token)
        ticket.refresh_from_db()
        return ticket, CheckInLog.Result.DUPLICATE

    ticket.refresh_from_db()
    _log(CheckInLog.Result.ALLOWED, ticket=ticket, volunteer=volunteer, token=token)
    return ticket, CheckInLog.Result.ALLOWED
