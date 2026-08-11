"""Throttles for the ticketing endpoints."""

from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class RegistrationRateThrottle(UserRateThrottle):
    """
    Caps registration attempts per account.

    Registration writes a row and holds a seat, so an unthrottled endpoint lets
    one script exhaust an event's capacity.

    This is a `UserRateThrottle`, not an `AnonRateThrottle`, and that is
    load-bearing: registration now requires authentication, and
    `AnonRateThrottle.get_cache_key` returns None for an authenticated request —
    it would count nothing at all and the cap would silently do nothing.
    """

    scope = 'registration'


class CheckInRateThrottle(UserRateThrottle):
    """
    Generous, but not unlimited.

    A volunteer scans continuously on event day, so this exists to bound a
    compromised volunteer account rather than to police normal use.
    """

    scope = 'checkin'
