"""
Ticketing models — registrations, orders, tickets, and the check-in audit log.

Two things drive the shape of this module:

1. A ticket must never exist without a paid order. `Ticket` rows are only
   created by `apps.ticketing.services.issue_ticket`, which is only reachable
   from `Order.mark_paid()`. There is no client-facing path to ticket creation.

2. Personal data is minimised. The CNIC is stored as a salted hash plus its last
   four digits: enough to enforce the one-registration-per-person rule and to
   eye-match an ID card at the door, without holding the number itself.
"""

import hashlib
import re
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.common.models import BaseModel, TimeStampedModel


def hash_identifier(raw):
    """
    Salted hash of a national ID / passport number.

    Salted with SECRET_KEY so the digests are useless outside this deployment;
    a bare SHA-256 of a CNIC is trivially reversible by brute force, since the
    format is short and highly structured.
    """
    normalised = re.sub(r'[^0-9A-Za-z]', '', raw or '').upper()
    if not normalised:
        return '', ''
    digest = hashlib.sha256(f'{settings.SECRET_KEY}:{normalised}'.encode()).hexdigest()
    return digest, normalised[-4:]


class RegistrationQuerySet(models.QuerySet):
    def holding_seats(self, event=None):
        """
        Registrations that currently occupy a seat.

        Confirmed registrations always count. Pending ones count too — a seat is
        held while payment is arranged — but only until the event's hold window
        expires, otherwise abandoned checkouts would sell out the room.
        """
        queryset = self.filter(
            status__in=[Registration.Status.PENDING, Registration.Status.CONFIRMED]
        )
        if event is not None:
            queryset = queryset.filter(event=event)
        return queryset.exclude(
            status=Registration.Status.PENDING,
            hold_expires_at__isnull=False,
            hold_expires_at__lt=timezone.now(),
        )


class Registration(BaseModel):
    """One person signing up for one event."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending payment'
        CONFIRMED = 'confirmed', 'Confirmed'
        CANCELLED = 'cancelled', 'Cancelled'
        EXPIRED = 'expired', 'Expired (seat released)'

    event = models.ForeignKey(
        'events.Event', related_name='registrations', on_delete=models.PROTECT
    )
    public_ref = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    full_name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=30)

    # See hash_identifier: the raw CNIC is never stored.
    cnic_hash = models.CharField(max_length=64, blank=True, editable=False)
    cnic_last4 = models.CharField(max_length=4, blank=True, editable=False)

    university = models.CharField(max_length=200, blank=True)
    occupation = models.CharField(max_length=200, blank=True)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    hold_expires_at = models.DateTimeField(null=True, blank=True, editable=False)

    objects = RegistrationQuerySet.as_manager()

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Registration'
        verbose_name_plural = 'Registrations'
        constraints = [
            # Enforced by the database, not just the serializer — two concurrent
            # requests can both pass a serializer-level uniqueness check.
            models.UniqueConstraint(
                fields=['event', 'email'],
                name='unique_registration_email_per_event',
            ),
            models.UniqueConstraint(
                fields=['event', 'cnic_hash'],
                condition=~models.Q(cnic_hash=''),
                name='unique_registration_cnic_per_event',
            ),
        ]
        indexes = [
            models.Index(fields=['event', 'status']),
        ]

    def set_cnic(self, raw):
        self.cnic_hash, self.cnic_last4 = hash_identifier(raw)

    @property
    def holds_a_seat(self):
        if self.status == self.Status.CONFIRMED:
            return True
        if self.status != self.Status.PENDING:
            return False
        return self.hold_expires_at is None or self.hold_expires_at >= timezone.now()

    def __str__(self):
        return f'{self.full_name} — {self.event.title}'


class Order(TimeStampedModel):
    """
    A payment attempt for one registration.

    `status` is only ever advanced server-side. Nothing a client sends can move
    an order to PAID: the free provider settles it during creation, and the
    manual provider requires a staff member to confirm it.
    """

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        AWAITING_CONFIRMATION = 'awaiting_confirmation', 'Awaiting confirmation'
        PAID = 'paid', 'Paid'
        FAILED = 'failed', 'Failed'
        CANCELLED = 'cancelled', 'Cancelled'
        REFUNDED = 'refunded', 'Refunded'

    registration = models.OneToOneField(
        Registration, related_name='order', on_delete=models.CASCADE
    )
    provider = models.CharField(max_length=40)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.PENDING)

    amount = models.DecimalField(max_digits=9, decimal_places=2)
    currency = models.CharField(max_length=3, default='PKR')

    reference = models.CharField(
        max_length=120,
        blank=True,
        help_text='Bank transfer reference, or the gateway transaction id.',
    )
    idempotency_key = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    raw_payload = models.JSONField(
        default=dict,
        blank=True,
        help_text='Whatever the provider sent us, kept for auditing a disputed payment.',
    )

    paid_at = models.DateTimeField(null=True, blank=True)
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='confirmed_orders',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        editable=False,
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'

    @property
    def is_paid(self):
        return self.status == self.Status.PAID

    def __str__(self):
        return f'{self.registration.full_name} — {self.get_status_display()}'


class TicketSequence(models.Model):
    """
    Per-event ticket counter.

    Kept out of `Event` so the ticketing app owns its own numbering, and so the
    row can be locked with `select_for_update()` without contending with edits
    to the event itself.

    `prefix` is resolved once, when the first ticket for the event is issued,
    and is then fixed. Two things depend on that:

    - Ticket numbers stay stable even if someone later edits the event's date
      or `ticket_prefix`.
    - It is unique across events. The natural prefix is derived from the year,
      so two events in the same year would otherwise both start at
      TEDX2026-0001 and collide on `Ticket.ticket_number`. The second event in
      a year gets TEDX2026-2, and so on — organizers wanting something prettier
      can set `Event.ticket_prefix` explicitly.
    """

    event = models.OneToOneField(
        'events.Event', related_name='ticket_sequence', on_delete=models.CASCADE
    )
    prefix = models.CharField(max_length=40, unique=True)
    last_number = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = 'Ticket Sequence'
        verbose_name_plural = 'Ticket Sequences'

    def __str__(self):
        return f'{self.event.title}: {self.last_number} issued ({self.prefix})'


class Ticket(TimeStampedModel):
    """
    An issued ticket. Created only by `services.issue_ticket`.

    Two separate tokens, deliberately:

    - `qr_token` is what the QR encodes and what a volunteer's scanner submits.
    - `access_token` is what the attendee's own ticket page uses.

    Keeping them apart means a screenshot of someone's ticket page URL shared in
    a group chat does not hand over the value the door scanner accepts.
    """

    registration = models.OneToOneField(
        Registration, related_name='ticket', on_delete=models.PROTECT
    )
    ticket_number = models.CharField(max_length=40, unique=True, editable=False)
    qr_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    access_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    checked_in = models.BooleanField(default=False)
    checked_in_at = models.DateTimeField(null=True, blank=True)
    checked_in_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='checked_in_tickets',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Ticket'
        verbose_name_plural = 'Tickets'
        indexes = [
            models.Index(fields=['checked_in']),
        ]

    @property
    def event(self):
        return self.registration.event

    @property
    def attendee_name(self):
        return self.registration.full_name

    def __str__(self):
        return self.ticket_number


class CheckInLog(models.Model):
    """
    Every scan attempt, including the ones that failed.

    The PRD asks for all attempts to be logged, so a rejected or unrecognised
    token is recorded too — that is exactly the trail you want when someone
    argues about being turned away at the door.
    """

    class Result(models.TextChoices):
        ALLOWED = 'allowed', 'Allowed'
        DUPLICATE = 'duplicate', 'Already checked in'
        INVALID = 'invalid', 'Invalid ticket'
        UNPAID = 'unpaid', 'Ticket not paid'
        WRONG_EVENT = 'wrong_event', 'Wrong event'
        CANCELLED = 'cancelled', 'Registration cancelled'

    ticket = models.ForeignKey(
        Ticket,
        related_name='check_in_logs',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    event = models.ForeignKey(
        'events.Event',
        related_name='check_in_logs',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    volunteer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='check_in_logs',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    scanned_token = models.CharField(
        max_length=100,
        blank=True,
        help_text='What was actually scanned, so unrecognised codes can be traced.',
    )
    result = models.CharField(max_length=20, choices=Result.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Check-in Log'
        verbose_name_plural = 'Check-in Logs'
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['result']),
        ]

    def __str__(self):
        return f'{self.get_result_display()} @ {self.created_at:%Y-%m-%d %H:%M}'
