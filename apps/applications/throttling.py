"""Throttles that keep the public submission endpoints from being flooded."""

from rest_framework.throttling import AnonRateThrottle


class SubmissionRateThrottle(AnonRateThrottle):
    """Applies to every public form POST (contact, applications)."""

    scope = 'submission'


class NewsletterRateThrottle(AnonRateThrottle):
    """Signups are cheap but still worth rate limiting."""

    scope = 'newsletter'
