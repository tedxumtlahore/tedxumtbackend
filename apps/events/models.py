"""
Events models - venues, events, and event schedule items.
"""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from apps.common.models import BaseModel
from apps.common.utils import generate_unique_slug


class Venue(BaseModel):
    name = models.CharField(max_length=200)
    address = models.TextField()
    city = models.CharField(max_length=100)
    google_maps = models.URLField(blank=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Venue'
        verbose_name_plural = 'Venues'

    def __str__(self):
        return f'{self.name} — {self.city}'


class Event(BaseModel):
    class EventTypeChoices(models.TextChoices):
        FLAGSHIP = 'flagship', 'Flagship'
        TALKS = 'talks', 'Talks'
        WORKSHOP = 'workshop', 'Workshop'
        PANEL = 'panel', 'Panel'
        COMMUNITY = 'community', 'Community'
        OTHER = 'other', 'Other'

    class StatusChoices(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        UPCOMING = 'upcoming', 'Upcoming'
        PAST = 'past', 'Past'
        CANCELLED = 'cancelled', 'Cancelled'

    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, editable=False)
    short_description = models.CharField(max_length=300)
    description = models.TextField()
    featured_image = models.ImageField(upload_to='events/featured/', blank=True)
    banner_image = models.ImageField(upload_to='events/banner/', blank=True)
    venue = models.ForeignKey(Venue, related_name='events', on_delete=models.PROTECT)
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    registration_url = models.URLField(blank=True)
    max_attendees = models.PositiveIntegerField(null=True, blank=True)
    event_type = models.CharField(max_length=20, choices=EventTypeChoices.choices)
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.DRAFT)
    is_featured = models.BooleanField(default=False)

    # ── Ticketing ──────────────────────────────────────────────────────────
    # `max_attendees` above doubles as the ticketing capacity — there is one
    # source of truth for how many people fit in the room.
    ticket_price = models.DecimalField(
        max_digits=9,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Set to 0 for a free event — tickets are then issued instantly.',
    )
    currency = models.CharField(max_length=3, default='PKR')
    ticket_prefix = models.CharField(
        max_length=20,
        blank=True,
        help_text='Ticket numbers look like TEDX2026-0001. Leave blank to derive from the year.',
    )
    registration_enabled = models.BooleanField(
        default=False,
        help_text='Master switch. Registration is closed unless this is ticked.',
    )
    registration_opens_at = models.DateTimeField(null=True, blank=True)
    registration_closes_at = models.DateTimeField(null=True, blank=True)
    registration_hold_minutes = models.PositiveIntegerField(
        default=1440,
        help_text=(
            'How long an unpaid registration holds a seat before the seat is '
            'released. 0 means a pending registration holds its seat forever.'
        ),
    )

    class Meta:
        ordering = ['-start_datetime', 'title']
        verbose_name = 'Event'
        verbose_name_plural = 'Events'

    def clean(self):
        super().clean()
        if self.start_datetime and self.end_datetime and self.end_datetime <= self.start_datetime:
            raise ValidationError({'end_datetime': 'The event must end after it starts.'})
        opens, closes = self.registration_opens_at, self.registration_closes_at
        if opens and closes and closes <= opens:
            raise ValidationError(
                {'registration_closes_at': 'Registration must close after it opens.'}
            )

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(self, self.title)
        super().save(*args, **kwargs)

    # ── Ticketing helpers ──────────────────────────────────────────────────
    # These are read by the ticketing app; the capacity check that actually
    # guards against overselling lives in apps.ticketing.services, where it can
    # run inside a locked transaction.

    @property
    def is_free(self):
        return self.ticket_price <= 0

    @property
    def resolved_ticket_prefix(self):
        if self.ticket_prefix:
            return self.ticket_prefix
        year = self.start_datetime.year if self.start_datetime else timezone.now().year
        return f'TEDX{year}'

    def seats_taken(self):
        """Registrations currently holding a seat (paid, or pending and unexpired)."""
        from apps.ticketing.models import Registration

        return Registration.objects.holding_seats(self).count()

    def seats_remaining(self):
        if not self.max_attendees:
            return None  # unlimited
        return max(0, self.max_attendees - self.seats_taken())

    @property
    def is_sold_out(self):
        remaining = self.seats_remaining()
        return remaining is not None and remaining <= 0

    def registration_closed_reason(self):
        """Why registration is shut, or None when it is open."""
        if self.status in {self.StatusChoices.DRAFT, self.StatusChoices.CANCELLED}:
            return 'This event is not open for registration.'
        if not self.registration_enabled:
            return 'Registration for this event has not opened yet.'

        now = timezone.now()
        if self.registration_opens_at and now < self.registration_opens_at:
            return 'Registration for this event has not opened yet.'
        if self.registration_closes_at and now > self.registration_closes_at:
            return 'Registration for this event has closed.'
        if self.is_sold_out:
            return 'This event is sold out.'
        return None

    @property
    def registration_is_open(self):
        return self.registration_closed_reason() is None

    def __str__(self):
        return self.title


class EventScheduleItem(BaseModel):
    event = models.ForeignKey(Event, related_name='schedule_items', on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    speaker = models.ForeignKey(
        'speakers.Speaker',
        related_name='event_schedule_items',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    start_time = models.TimeField()
    end_time = models.TimeField()
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['event', 'start_time', 'title']
        verbose_name = 'Event Schedule Item'
        verbose_name_plural = 'Event Schedule Items'

    def clean(self):
        super().clean()
        if self.start_time and self.end_time and self.end_time <= self.start_time:
            raise ValidationError({'end_time': 'The session must end after it starts.'})

    def __str__(self):
        return f'{self.event.title} — {self.title}'
