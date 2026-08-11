"""
Attendee account serializers.

Attendees share Django's `auth.User` table with staff and volunteers. What
separates them is what they are *not*: `is_staff=False` and no group
membership, so an attendee passes `IsAuthenticated` and fails every one of
`IsStaffOrReadOnly`, `IsVolunteer` and `IsOrganizer`. Adding accounts therefore
grants no access to the CMS, the scanner, or the organizer dashboard.

The email doubles as the username. Attendees think of themselves as an email
address, and a separate username would be one more thing to forget.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

User = get_user_model()


class AccountRegisterSerializer(serializers.Serializer):
    """Create an attendee account."""

    full_name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})

    def validate_email(self, value):
        email = value.strip().lower()
        # Checked here for a clean field error; the database's unique constraint
        # on username is what actually prevents a race between two signups.
        if User.objects.filter(username__iexact=email).exists():
            raise serializers.ValidationError('An account with this email already exists.')
        return email

    def validate_password(self, value):
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages)) from exc
        return value

    def create(self, validated_data):
        full_name = validated_data['full_name'].strip()
        first, _, last = full_name.partition(' ')
        return User.objects.create_user(
            username=validated_data['email'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=first[:150],
            last_name=last[:150],
            is_staff=False,
        )


class AccountSerializer(serializers.ModelSerializer):
    """
    Who the caller is.

    The three role flags let the frontend decide what to offer — a volunteer
    signing in on the public site should still see their way to the scanner.
    They are derived from groups and never writable.
    """

    full_name = serializers.SerializerMethodField()
    is_volunteer = serializers.SerializerMethodField()
    is_organizer = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'full_name', 'email', 'is_staff', 'is_volunteer', 'is_organizer']
        read_only_fields = fields

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username

    def get_is_volunteer(self, obj):
        from apps.common.permissions import VOLUNTEERS_GROUP, in_group

        return in_group(obj, VOLUNTEERS_GROUP)

    def get_is_organizer(self, obj):
        from apps.common.permissions import ORGANIZERS_GROUP, in_group

        return in_group(obj, ORGANIZERS_GROUP)


class ClaimRegistrationSerializer(serializers.Serializer):
    """
    Attach an existing registration to the signed-in account.

    Ownership is proved by possessing `public_ref` — the unguessable UUID handed
    to the attendee when they registered. Matching on email instead would let
    anyone claim a stranger's ticket by signing up with their address, which is
    only safe once addresses are verified, and no SMTP is connected yet.

    Possessing `public_ref` already grants full status access today, so claiming
    exposes nothing that the link did not.
    """

    public_ref = serializers.UUIDField()
