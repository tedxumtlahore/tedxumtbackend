"""
Ticket email delivery.

Two rules shape this module:

1. **A mail failure must never cost someone their ticket.** The ticket is the
   database row, not the email. Sending happens after the transaction commits,
   and every failure is caught and logged rather than raised — otherwise a
   flaky SMTP server would roll back a paid registration.

2. **The email must be re-sendable.** Because delivery is best-effort, there
   has to be a way to try again: `send_ticket_email` is idempotent and is wired
   to both an admin action and a staff endpoint.

There is no task queue in this project, so sending is synchronous. At the
volume of a single event that is fine — a few hundred emails spread across the
days people register. Before a large on-sale, move this behind Celery; the
call sites would not change.
"""

import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone

from .links import qr_payload, ticket_url
from .rendering import ticket_pdf

logger = logging.getLogger('apps.ticketing')


# Re-exported so existing callers keep working; the canonical definitions
# live in links.py because the API, the PDF, and the email must all encode the
# same URL.
build_qr_payload = qr_payload
build_ticket_url = ticket_url


def send_ticket_email(ticket, *, base_url=None, fail_silently=True):
    """
    Email the attendee their ticket with the PDF attached.

    Returns True if the message was handed to the mail backend. Never raises
    when `fail_silently` (the default) — callers are in the middle of issuing a
    ticket and must not be interrupted by a mail problem.
    """
    registration = ticket.registration
    event = registration.event

    context = {
        'ticket': ticket,
        'registration': registration,
        'event': event,
        'venue': getattr(event, 'venue', None),
        'attendee_name': registration.full_name,
        'ticket_number': ticket.ticket_number,
        'ticket_url': build_ticket_url(ticket, base_url=base_url),
        'event_start': timezone.localtime(event.start_datetime) if event.start_datetime else None,
        'site_name': 'TEDxUMT Lahore',
    }

    try:
        subject = f'Your ticket for {event.title} — {ticket.ticket_number}'
        body = render_to_string('ticketing/ticket_email.txt', context)
        html = render_to_string('ticketing/ticket_email.html', context)

        message = EmailMultiAlternatives(
            subject=subject,
            body=body,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
            to=[registration.email],
        )
        message.attach_alternative(html, 'text/html')
        message.attach(
            f'{ticket.ticket_number}.pdf',
            ticket_pdf(ticket, qr_payload=build_qr_payload(ticket, base_url=base_url)),
            'application/pdf',
        )
        message.send(fail_silently=False)
    except Exception:
        # Logged, not raised: the attendee still has a valid ticket they can
        # view online, and an organizer can resend from the admin.
        logger.exception('Could not email ticket %s to %s', ticket.ticket_number, registration.email)
        if not fail_silently:
            raise
        return False

    logger.info('Emailed ticket %s to %s', ticket.ticket_number, registration.email)
    return True
