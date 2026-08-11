"""
Attendee account endpoints.

The security property that matters here: `/me/registrations/` is the first
endpoint in this project keyed on *identity* rather than on an unguessable
token. Every other attendee endpoint is reachable only by holding a `public_ref`
or an `access_token`, which is what keeps the attendee list from being
enumerable (see the "no public lookup by ticket number" decision).

So the queryset is filtered on `request.user` directly and never on anything the
client sends. There is deliberately no `?user=` parameter and no detail route
that takes a registration id.
"""

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from apps.ticketing.models import Registration
from apps.ticketing.serializers import RegistrationSerializer

from .serializers import AccountRegisterSerializer, AccountSerializer, ClaimRegistrationSerializer
from .throttling import AccountCreateRateThrottle

User = get_user_model()


def _token_pair(user):
    refresh = RefreshToken.for_user(user)
    return {'access': str(refresh.access_token), 'refresh': str(refresh)}


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([AccountCreateRateThrottle])
def register_account_view(request):
    """
    POST /api/accounts/register/ — create an attendee account.

    Returns a token pair so signing up does not immediately require signing in.
    """
    serializer = AccountRegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
        with transaction.atomic():
            user = serializer.save()
    except IntegrityError:
        # Two signups raced past the serializer's existence check; the unique
        # constraint on username is the real guard.
        return Response(
            {
                'success': False,
                'message': 'An account with this email already exists.',
                'errors': {'email': ['An account with this email already exists.']},
                'status_code': status.HTTP_409_CONFLICT,
            },
            status=status.HTTP_409_CONFLICT,
        )

    return Response(
        {
            'success': True,
            'message': 'Account created.',
            'user': AccountSerializer(user).data,
            'tokens': _token_pair(user),
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me_view(request):
    """GET /api/accounts/me/ — who the caller is."""
    return Response(AccountSerializer(request.user).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_registrations_view(request):
    """
    GET /api/accounts/me/registrations/ — the caller's own registrations.

    Filtered on `request.user`. Nothing the client sends narrows or widens this.
    """
    registrations = (
        Registration.objects.filter(user=request.user)
        .select_related('event', 'order', 'ticket')
        .order_by('-created_at')
    )
    return Response(
        {
            'count': registrations.count(),
            'results': RegistrationSerializer(
                registrations, many=True, context={'request': request}
            ).data,
        }
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def claim_registration_view(request):
    """
    POST /api/accounts/me/registrations/claim/ — attach a past registration.

    For someone who registered before creating an account. They prove ownership
    with the `public_ref` from their registration link.
    """
    serializer = ClaimRegistrationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    registration = Registration.objects.filter(
        public_ref=serializer.validated_data['public_ref']
    ).select_related('event', 'order', 'ticket').first()

    if registration is None:
        return Response(
            {
                'success': False,
                'message': 'No registration found for that reference.',
                'errors': {'public_ref': ['No registration found for that reference.']},
                'status_code': status.HTTP_404_NOT_FOUND,
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    if registration.user_id and registration.user_id != request.user.id:
        # Already attached to a different account. Silent reassignment would let
        # a leaked reference move someone else's ticket into a stranger's list.
        return Response(
            {
                'success': False,
                'message': 'That registration is already linked to another account.',
                'errors': {},
                'code': 'already_claimed',
                'status_code': status.HTTP_409_CONFLICT,
            },
            status=status.HTTP_409_CONFLICT,
        )

    if not registration.user_id:
        registration.user = request.user
        registration.save(update_fields=['user', 'updated_at'])

    return Response(
        {
            'success': True,
            'message': 'Registration added to your account.',
            'registration': RegistrationSerializer(
                registration, context={'request': request}
            ).data,
        }
    )
