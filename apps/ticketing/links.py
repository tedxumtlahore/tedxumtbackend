"""
Public URLs for a ticket.

These point at the **website**, not the API. The two are different origins in
every deployment — different ports in development, different hosts in
production — so building them from the incoming request produces a URL on the
API host, where `/checkin/<token>` does not exist. A QR built that way scans to
a 404.

`TICKET_BASE_URL` is therefore the source of truth, with the request host only
as a last resort for a same-origin setup.
"""

from django.conf import settings


def public_base_url(request=None):
    configured = (getattr(settings, 'TICKET_BASE_URL', '') or '').rstrip('/')
    if configured:
        return configured
    if request is not None:
        return request.build_absolute_uri('/').rstrip('/')
    return ''


def qr_payload(ticket, *, request=None, base_url=None):
    """What the QR encodes — the check-in route on the public site."""
    base = (base_url or '').rstrip('/') or public_base_url(request)
    return f'{base}/checkin/{ticket.qr_token}'


def ticket_url(ticket, *, request=None, base_url=None):
    """Where the attendee views their own ticket."""
    base = (base_url or '').rstrip('/') or public_base_url(request)
    return f'{base}/ticket/{ticket.access_token}'
