"""
Ticketing serializers.

Field exposure is the security boundary here, so it is worth being explicit:

- The raw CNIC is accepted on input and immediately hashed. It is write-only
  and appears in no response.
- `qr_token` is never serialized to an attendee. It is the value the door
  scanner accepts; the attendee's own page uses `access_token` instead.
- Order status is read-only everywhere. Nothing a client sends can mark an
  order paid.
"""

import re

from rest_framework import serializers

from .links import qr_payload
from .models import CheckInLog, Order, PaymentAccount, Registration, Ticket

CNIC_PATTERN = re.compile(r'^[0-9A-Za-z\-\s]{6,25}$')


class RegistrationCreateSerializer(serializers.Serializer):
    """Input for `POST /api/registrations/`. Deliberately not a ModelSerializer.

    The model's uniqueness constraints span (event, email) and a hashed CNIC,
    neither of which a ModelSerializer can validate meaningfully — and the real
    check has to happen inside the locked transaction in `services.register`
    anyway. Keeping this a plain Serializer stops DRF from adding a second,
    weaker uniqueness check that would race.
    """

    full_name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=30)
    cnic = serializers.CharField(max_length=25, required=False, allow_blank=True, write_only=True)
    university = serializers.CharField(max_length=200, required=False, allow_blank=True)
    occupation = serializers.CharField(max_length=200, required=False, allow_blank=True)

    def validate_full_name(self, value):
        cleaned = value.strip()
        if len(cleaned) < 2:
            raise serializers.ValidationError('Please enter your full name.')
        return cleaned

    def validate_email(self, value):
        return value.strip().lower()

    def validate_phone(self, value):
        cleaned = value.strip()
        digits = re.sub(r'\D', '', cleaned)
        if len(digits) < 7:
            raise serializers.ValidationError('Please enter a valid phone number.')
        return cleaned

    def validate_cnic(self, value):
        cleaned = (value or '').strip()
        if cleaned and not CNIC_PATTERN.match(cleaned):
            raise serializers.ValidationError(
                'Enter a valid CNIC or passport number.'
            )
        return cleaned


class PaymentAccountSerializer(serializers.ModelSerializer):
    """Public — these are collection accounts, meant to be handed out."""

    provider_label = serializers.CharField(source='get_provider_display', read_only=True)

    class Meta:
        model = PaymentAccount
        fields = [
            'id', 'provider', 'provider_label', 'account_title', 'account_number',
            'bank_name', 'iban', 'note',
        ]
        read_only_fields = fields


class PaymentProofSerializer(serializers.Serializer):
    """
    What the attendee submits after transferring.

    `proof` is write-only and the stored image is never serialized back — a
    payment screenshot usually shows the sender's balance and recent history.
    """

    reference = serializers.CharField(max_length=120, required=False, allow_blank=True)
    paid_from_number = serializers.CharField(max_length=30, required=False, allow_blank=True)
    proof = serializers.ImageField(required=False, write_only=True)

    def validate(self, attrs):
        if not any(attrs.get(field) for field in ('reference', 'paid_from_number', 'proof')):
            raise serializers.ValidationError(
                'Give us the transaction ID, the number you paid from, or a screenshot — '
                'otherwise we cannot match your payment.'
            )
        return attrs

    def validate_reference(self, value):
        return (value or '').strip()

    def validate_paid_from_number(self, value):
        return (value or '').strip()


class RegistrationSerializer(serializers.ModelSerializer):
    """The attendee's own view of their registration, fetched by `public_ref`."""

    event_title = serializers.CharField(source='event.title', read_only=True)
    event_slug = serializers.CharField(source='event.slug', read_only=True)
    payment_status = serializers.CharField(source='order.status', read_only=True)
    payment_reference = serializers.CharField(source='order.reference', read_only=True)
    proof_submitted = serializers.SerializerMethodField()
    amount = serializers.DecimalField(
        source='order.amount', max_digits=9, decimal_places=2, read_only=True
    )
    currency = serializers.CharField(source='order.currency', read_only=True)
    ticket_number = serializers.CharField(source='ticket.ticket_number', read_only=True)
    ticket_access_token = serializers.UUIDField(source='ticket.access_token', read_only=True)

    class Meta:
        model = Registration
        fields = [
            'public_ref', 'event_title', 'event_slug', 'full_name', 'email', 'phone',
            'university', 'occupation', 'status', 'payment_status', 'payment_reference',
            'proof_submitted', 'amount', 'currency',
            'ticket_number', 'ticket_access_token', 'created_at',
        ]
        read_only_fields = fields

    def get_proof_submitted(self, obj):
        order = getattr(obj, 'order', None)
        return bool(order and order.proof_submitted_at)


class RegistrationAdminSerializer(serializers.ModelSerializer):
    """Staff view. Adds the CNIC's last four digits — never the whole number."""

    event_title = serializers.CharField(source='event.title', read_only=True)
    payment_status = serializers.CharField(source='order.status', read_only=True)
    payment_reference = serializers.CharField(source='order.reference', read_only=True)
    ticket_number = serializers.CharField(source='ticket.ticket_number', read_only=True)
    checked_in = serializers.BooleanField(source='ticket.checked_in', read_only=True)
    holds_a_seat = serializers.BooleanField(read_only=True)

    class Meta:
        model = Registration
        fields = [
            'id', 'public_ref', 'event', 'event_title', 'full_name', 'email', 'phone',
            'cnic_last4', 'university', 'occupation', 'status', 'holds_a_seat',
            'payment_status', 'payment_reference', 'ticket_number', 'checked_in',
            'hold_expires_at', 'created_at', 'updated_at',
        ]
        read_only_fields = fields


class TicketSerializer(serializers.ModelSerializer):
    """
    The attendee's ticket.

    `qr_payload` is included because the attendee needs it to render their own
    QR code — it is their ticket. It is reachable only via the unguessable
    `access_token`, never by walking ticket numbers.
    """

    attendee_name = serializers.CharField(read_only=True)
    event_title = serializers.CharField(source='registration.event.title', read_only=True)
    event_slug = serializers.CharField(source='registration.event.slug', read_only=True)
    event_start = serializers.DateTimeField(
        source='registration.event.start_datetime', read_only=True
    )
    venue_name = serializers.CharField(source='registration.event.venue.name', read_only=True)
    venue_address = serializers.CharField(
        source='registration.event.venue.address', read_only=True
    )
    registration_ref = serializers.UUIDField(source='registration.public_ref', read_only=True)
    qr_payload = serializers.SerializerMethodField()

    class Meta:
        model = Ticket
        fields = [
            'ticket_number', 'attendee_name', 'event_title', 'event_slug', 'event_start',
            'venue_name', 'venue_address', 'registration_ref', 'qr_payload',
            'checked_in', 'checked_in_at', 'created_at',
        ]
        read_only_fields = fields

    def get_qr_payload(self, obj):
        """
        The check-in URL the QR encodes — on the public site, not the API.
        Built from TICKET_BASE_URL, because the request host is the API host and
        a QR pointing there scans to a 404.
        """
        return qr_payload(obj, request=self.context.get('request'))


class TicketAdminSerializer(serializers.ModelSerializer):
    """Staff listing. Excludes both tokens — staff have no need to scan them."""

    attendee_name = serializers.CharField(read_only=True)
    attendee_email = serializers.EmailField(source='registration.email', read_only=True)
    event_title = serializers.CharField(source='registration.event.title', read_only=True)
    checked_in_by_username = serializers.CharField(
        source='checked_in_by.username', read_only=True, default=None
    )

    class Meta:
        model = Ticket
        fields = [
            'id', 'ticket_number', 'attendee_name', 'attendee_email', 'event_title',
            'checked_in', 'checked_in_at', 'checked_in_by_username', 'created_at',
        ]
        read_only_fields = fields


class CheckInRequestSerializer(serializers.Serializer):
    """What a scanner submits. Accepts the bare token or the whole scanned URL."""

    token = serializers.CharField(max_length=200)
    event = serializers.SlugField(required=False, allow_blank=True)


class CheckInResultSerializer(serializers.Serializer):
    """
    What the scanner shows the volunteer.

    Attendee details are included only when there is a ticket to describe —
    an unrecognised code returns the failure and nothing else.
    """

    result = serializers.CharField()
    allowed = serializers.BooleanField()
    message = serializers.CharField()
    ticket_number = serializers.CharField(required=False)
    attendee_name = serializers.CharField(required=False)
    cnic_last4 = serializers.CharField(required=False)
    event_title = serializers.CharField(required=False)
    checked_in_at = serializers.DateTimeField(required=False, allow_null=True)


class CheckInLogSerializer(serializers.ModelSerializer):
    ticket_number = serializers.CharField(source='ticket.ticket_number', read_only=True, default=None)
    attendee_name = serializers.CharField(
        source='ticket.registration.full_name', read_only=True, default=None
    )
    event_title = serializers.CharField(source='event.title', read_only=True, default=None)
    volunteer_username = serializers.CharField(
        source='volunteer.username', read_only=True, default=None
    )

    class Meta:
        model = CheckInLog
        fields = [
            'id', 'ticket_number', 'attendee_name', 'event_title',
            'volunteer_username', 'result', 'created_at',
        ]
        read_only_fields = fields


class OrderAdminSerializer(serializers.ModelSerializer):
    attendee_name = serializers.CharField(source='registration.full_name', read_only=True)
    event_title = serializers.CharField(source='registration.event.title', read_only=True)
    confirmed_by_username = serializers.CharField(
        source='confirmed_by.username', read_only=True, default=None
    )
    has_proof = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'attendee_name', 'event_title', 'provider', 'status', 'amount',
            'currency', 'reference', 'paid_from_number', 'has_proof', 'proof_submitted_at',
            'paid_at', 'confirmed_by_username', 'created_at',
        ]
        # Status is advanced only through services.mark_paid, never by a PATCH.
        read_only_fields = fields

    def get_has_proof(self, obj):
        """Whether the attendee has reported their transfer yet."""
        return bool(obj.proof_submitted_at)
