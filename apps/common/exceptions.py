"""
Project-wide DRF exception handling.

Every API error comes back in one shape so the frontend can render it without
special-casing per endpoint:

    {"success": false, "message": "...", "errors": {...}, "status_code": 400}
"""

import logging

from django.core.exceptions import PermissionDenied
from django.http import Http404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger('apps.api')

GENERIC_MESSAGES = {
    status.HTTP_400_BAD_REQUEST: 'Please check the highlighted fields and try again.',
    status.HTTP_401_UNAUTHORIZED: 'You need to sign in to do that.',
    status.HTTP_403_FORBIDDEN: 'You do not have permission to do that.',
    status.HTTP_404_NOT_FOUND: 'That resource could not be found.',
    status.HTTP_405_METHOD_NOT_ALLOWED: 'That action is not supported here.',
    status.HTTP_429_TOO_MANY_REQUESTS: 'Too many requests — please slow down and try again shortly.',
}


def _first_message(detail):
    """Pull a human-readable sentence out of DRF's nested error structure."""
    if isinstance(detail, str):
        return detail
    if isinstance(detail, list) and detail:
        return _first_message(detail[0])
    if isinstance(detail, dict):
        for value in detail.values():
            message = _first_message(value)
            if message:
                return message
    return None


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is None:
        if isinstance(exc, Http404):
            response = Response(status=status.HTTP_404_NOT_FOUND)
        elif isinstance(exc, PermissionDenied):
            response = Response(status=status.HTTP_403_FORBIDDEN)
        else:
            # Unhandled — let Django's own 500 machinery log and report it.
            logger.exception('Unhandled API exception in %s', context.get('view'))
            return None

    detail = response.data if isinstance(response.data, (dict, list)) else {'detail': response.data}
    errors = detail if isinstance(detail, dict) else {'detail': detail}

    response.data = {
        'success': False,
        'message': _first_message(detail) or GENERIC_MESSAGES.get(
            response.status_code, 'Something went wrong.'
        ),
        'errors': errors,
        'status_code': response.status_code,
    }
    return response
