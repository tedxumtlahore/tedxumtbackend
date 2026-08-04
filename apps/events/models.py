"""
Events models - venues, events, and event schedule items.
"""

from django.db import models
from django.utils.text import slugify

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

    class Meta:
        ordering = ['-start_datetime', 'title']
        verbose_name = 'Event'
        verbose_name_plural = 'Events'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(self, self.title)
        super().save(*args, **kwargs)

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

    def __str__(self):
        return f'{self.event.title} — {self.title}'
