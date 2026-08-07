"""Throttles for the ticketing endpoints."""

from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class RegistrationRateThrottle(AnonRateThrottle):
    """
    Caps registration attempts per IP.

    Registration writes a row and holds a seat, so an unthrottled endpoint lets
    one script exhaust an event's capacity.
    """

    scope = 'registration'


class CheckInRateThrottle(UserRateThrottle):
    """
    Generous, but not unlimited.

    A volunteer scans continuously on event day, so this exists to bound a
    compromised volunteer account rather than to police normal use.
    """

    scope = 'checkin'
