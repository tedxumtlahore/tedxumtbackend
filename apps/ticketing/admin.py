"""
Ticketing admin — the organizers' desk.

Registrations and tickets are created by the public API, not typed in here, so
`has_add_permission` is off and the submitted fields are read-only. The one
action that genuinely matters is "Confirm payment": it is the human step that
turns a bank transfer into an issued ticket.
"""

from django.contrib import admin, messages
from django.utils.html import format_html

from .models import CheckInLog, Order, PaymentAccount, Registration, Ticket, TicketSequence
from .services import TicketingError, deliver_ticket, mark_paid


class OrderInline(admin.StackedInline):
    model = Order
    extra = 0
    can_delete = False
    readonly_fields = [
        'provider', 'status', 'amount', 'currency', 'reference',
        'paid_from_number', 'proof_preview', 'proof_submitted_at',
        'paid_at', 'confirmed_by', 'idempotency_key', 'raw_payload',
    ]
    fields = readonly_fields

    def has_add_permission(self, request, obj=None):
        return False

    @admin.display(description='Payment screenshot')
    def proof_preview(self, obj):
        """Shown so confirming is a glance at the statement, not a hunt."""
        if obj.pk and obj.payment_proof:
            return format_html(
                '<a href="{}" target="_blank" rel="noopener">'
                '<img src="{}" style="max-height:260px;border-radius:6px" /></a>',
                obj.payment_proof.url, obj.payment_proof.url,
            )
        return '— not submitted'


class TicketInline(admin.StackedInline):
    model = Ticket
    extra = 0
    can_delete = False
    readonly_fields = [
        'ticket_number', 'checked_in', 'checked_in_at', 'checked_in_by', 'created_at',
    ]
    # qr_token and access_token are deliberately absent: an organizer browsing
    # the admin has no reason to see a value the door scanner would accept.
    fields = readonly_fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display = [
        'full_name', 'email', 'event', 'status', 'payment_status',
        'paid_from', 'proof_flag', 'ticket_number', 'checked_in_display', 'created_at',
    ]
    list_display_links = ['full_name']
    list_filter = ['status', 'event', 'created_at']
    search_fields = ['full_name', 'email', 'phone', 'university', 'occupation', 'cnic_last4']
    list_select_related = ['event', 'order', 'ticket']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    inlines = [OrderInline, TicketInline]
    actions = ['confirm_payment', 'cancel_registration']

    readonly_fields = [
        'public_ref', 'event', 'full_name', 'email', 'phone', 'cnic_last4',
        'university', 'occupation', 'hold_expires_at', 'created_at', 'updated_at',
    ]
    fieldsets = (
        ('Attendee', {
            'fields': ('full_name', 'email', 'phone', 'cnic_last4', 'university', 'occupation'),
            'description': (
                'Only the last four digits of the CNIC are stored — enough to match '
                'an ID card at the door without holding the number itself.'
            ),
        }),
        ('Registration', {'fields': ('event', 'public_ref', 'status', 'hold_expires_at')}),
        ('System', {'fields': ('is_active', 'created_at', 'updated_at')}),
    )

    def has_add_permission(self, request):
        return False

    @admin.display(description='Payment')
    def payment_status(self, obj):
        order = getattr(obj, 'order', None)
        return order.get_status_display() if order else '—'

    @admin.display(description='Paid from')
    def paid_from(self, obj):
        """The number to look for on the statement."""
        order = getattr(obj, 'order', None)
        return (order.paid_from_number or '—') if order else '—'

    @admin.display(description='Proof', boolean=True)
    def proof_flag(self, obj):
        order = getattr(obj, 'order', None)
        return bool(order and order.proof_submitted_at)

    @admin.display(description='Ticket')
    def ticket_number(self, obj):
        ticket = getattr(obj, 'ticket', None)
        return ticket.ticket_number if ticket else '—'

    @admin.display(description='Checked in', boolean=True)
    def checked_in_display(self, obj):
        ticket = getattr(obj, 'ticket', None)
        return bool(ticket and ticket.checked_in)

    @admin.action(description='Confirm payment and issue ticket')
    def confirm_payment(self, request, queryset):
        """
        The human step for bank transfers.

        Check the money actually arrived before using this — it is what issues
        the ticket and emails the attendee.
        """
        issued, skipped, failed = 0, 0, 0
        for registration in queryset.select_related('order'):
            order = getattr(registration, 'order', None)
            if order is None:
                failed += 1
                continue
            if order.is_paid:
                skipped += 1
                continue
            try:
                mark_paid(order, confirmed_by=request.user)
                issued += 1
            except TicketingError as exc:
                failed += 1
                self.message_user(
                    request, f'{registration.full_name}: {exc.message}', level=messages.ERROR
                )

        if issued:
            self.message_user(request, f'{issued} payment(s) confirmed and ticket(s) issued.')
        if skipped:
            self.message_user(request, f'{skipped} already paid — left alone.', level=messages.WARNING)
        if failed and not issued:
            self.message_user(request, 'No payments were confirmed.', level=messages.ERROR)

    @admin.action(description='Cancel selected registrations')
    def cancel_registration(self, request, queryset):
        count = queryset.update(status=Registration.Status.CANCELLED)
        self.message_user(request, f'{count} registration(s) cancelled; their seats are released.')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'attendee', 'event', 'provider', 'status', 'amount', 'paid_at', 'confirmed_by',
    ]
    list_display_links = ['id', 'attendee']
    list_filter = ['status', 'provider', 'created_at']
    search_fields = ['reference', 'registration__full_name', 'registration__email']
    list_select_related = ['registration', 'registration__event', 'confirmed_by']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    readonly_fields = [
        'registration', 'provider', 'amount', 'currency', 'idempotency_key',
        'paid_at', 'confirmed_by', 'raw_payload', 'created_at', 'updated_at',
    ]

    def has_add_permission(self, request):
        return False

    @admin.display(description='Attendee')
    def attendee(self, obj):
        return obj.registration.full_name

    @admin.display(description='Event')
    def event(self, obj):
        return obj.registration.event.title


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = [
        'ticket_number', 'attendee_name', 'event_title',
        'checked_in', 'checked_in_at', 'checked_in_by',
    ]
    list_display_links = ['ticket_number']
    list_filter = ['checked_in', 'registration__event', 'created_at']
    search_fields = [
        'ticket_number', 'registration__full_name', 'registration__email',
    ]
    list_select_related = ['registration', 'registration__event', 'checked_in_by']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    actions = ['resend_ticket_email', 'undo_check_in']

    readonly_fields = [
        'registration', 'ticket_number', 'token_note',
        'checked_in_at', 'checked_in_by', 'created_at', 'updated_at',
    ]
    fieldsets = (
        ('Ticket', {'fields': ('registration', 'ticket_number', 'token_note')}),
        ('Check-in', {'fields': ('checked_in', 'checked_in_at', 'checked_in_by')}),
        ('System', {'fields': ('created_at', 'updated_at')}),
    )

    def has_add_permission(self, request):
        return False

    @admin.display(description='Event')
    def event_title(self, obj):
        return obj.registration.event.title

    @admin.display(description='QR token')
    def token_note(self, obj):
        # Showing the token here would let anyone with admin read access check
        # a ticket in from their desk. The attendee's emailed ticket is the
        # only place it appears.
        return format_html('<em>Hidden — the QR token is only on the attendee\'s ticket.</em>')

    @admin.action(description='Resend ticket email')
    def resend_ticket_email(self, request, queryset):
        """Email delivery is best effort, so organizers need a retry button."""
        sent, failed = 0, 0
        for ticket in queryset.select_related('registration', 'registration__event'):
            if deliver_ticket(ticket):
                sent += 1
            else:
                failed += 1

        if sent:
            self.message_user(request, f'{sent} ticket email(s) sent.')
        if failed:
            self.message_user(
                request,
                f'{failed} could not be sent — check the mail settings and the server log.',
                level=messages.ERROR,
            )

    @admin.action(description='Undo check-in (let the attendee scan again)')
    def undo_check_in(self, request, queryset):
        count = queryset.filter(checked_in=True).update(
            checked_in=False, checked_in_at=None, checked_in_by=None
        )
        self.message_user(request, f'{count} ticket(s) reopened for scanning.')


@admin.register(CheckInLog)
class CheckInLogAdmin(admin.ModelAdmin):
    list_display = ['created_at', 'result', 'ticket', 'attendee', 'event', 'volunteer']
    list_filter = ['result', 'event', 'created_at']
    search_fields = ['ticket__ticket_number', 'ticket__registration__full_name', 'scanned_token']
    list_select_related = ['ticket', 'ticket__registration', 'event', 'volunteer']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    readonly_fields = ['ticket', 'event', 'volunteer', 'scanned_token', 'result', 'created_at']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        # An audit trail you can edit is not an audit trail.
        return False

    @admin.display(description='Attendee')
    def attendee(self, obj):
        return obj.ticket.registration.full_name if obj.ticket else '—'


@admin.register(PaymentAccount)
class PaymentAccountAdmin(admin.ModelAdmin):
    """
    The accounts attendees send money to.

    Whatever is ticked visible here is what appears on the payment page, so
    check the number carefully — a typo sends every attendee's money to a
    stranger.
    """

    list_display = ['provider', 'account_title', 'account_number', 'order', 'is_visible']
    list_editable = ['order', 'is_visible']
    list_display_links = ['provider']
    list_filter = ['provider', 'is_visible', 'is_active']
    search_fields = ['account_title', 'account_number', 'bank_name', 'iban']
    ordering = ['order', 'provider']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Account', {
            'fields': ('provider', 'account_title', 'account_number'),
            'description': (
                'The account title is what attendees see before sending — it should '
                'match the name on the receiving account exactly, or people will '
                'hesitate to pay.'
            ),
        }),
        ('Bank only', {'fields': ('bank_name', 'iban'), 'classes': ('collapse',)}),
        ('Display', {'fields': ('note', 'order', 'is_visible')}),
        ('System', {'fields': ('is_active', 'created_at', 'updated_at')}),
    )


@admin.register(TicketSequence)
class TicketSequenceAdmin(admin.ModelAdmin):
    list_display = ['event', 'last_number']
    readonly_fields = ['event', 'last_number']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        # Editing the counter by hand would produce duplicate ticket numbers.
        return False
