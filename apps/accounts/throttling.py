"""Throttles for account endpoints."""

from rest_framework.throttling import AnonRateThrottle


class AccountCreateRateThrottle(AnonRateThrottle):
    """
    Caps account creation per IP.

    Creating an account is cheap for the caller and permanent for us, so an
    unthrottled endpoint is an invitation to fill the user table. The rate is
    set in DEFAULT_THROTTLE_RATES under the 'account' scope.
    """

    scope = 'account'
