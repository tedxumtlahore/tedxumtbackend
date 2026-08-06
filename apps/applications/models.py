"""
Applications models - everything the public submits to us.

Contact messages, newsletter signups, and the speaker/volunteer/partner
application forms. All of these are write-only from the website and are
triaged by organizers in the Django admin.
"""

from django.db import models

from apps.common.models import BaseModel, TimeStampedModel


class SubmissionStatusChoices(models.TextChoices):
    NEW = 'new', 'New'
    IN_REVIEW = 'in_review', 'In Review'
    ACCEPTED = 'accepted', 'Accepted'
    REJECTED = 'rejected', 'Rejected'
    ARCHIVED = 'archived', 'Archived'


class SubmissionModel(BaseModel):
    """Shared triage fields for every public submission."""

    status = models.CharField(
        max_length=20,
        choices=SubmissionStatusChoices.choices,
        default=SubmissionStatusChoices.NEW,
    )
    internal_notes = models.TextField(
        blank=True,
        help_text='Private — never exposed through the API.',
    )
    submitted_ip = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        abstract = True
        ordering = ['-created_at']


class ContactMessage(SubmissionModel):
    """A message sent from the Contact page form."""

    name = models.CharField(max_length=150)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)

    class Meta(SubmissionModel.Meta):
        verbose_name = 'Contact Message'
        verbose_name_plural = 'Contact Messages'

    def __str__(self):
        return f'{self.name} — {self.subject}'


class NewsletterSubscriber(TimeStampedModel):
    """An email address subscribed to the announcements list."""

    email = models.EmailField(unique=True)
    name = models.CharField(max_length=150, blank=True)
    is_subscribed = models.BooleanField(default=True)
    unsubscribed_at = models.DateTimeField(null=True, blank=True)
    source = models.CharField(
        max_length=50,
        default='website',
        help_text='Where the signup came from (website, event, import, ...).',
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Newsletter Subscriber'
        verbose_name_plural = 'Newsletter Subscribers'

    def __str__(self):
        return self.email


class SpeakerApplication(SubmissionModel):
    """A pitch submitted through the Apply page."""

    full_name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=30, blank=True)
    organization = models.CharField(max_length=200, blank=True)
    designation = models.CharField(max_length=200, blank=True)
    talk_title = models.CharField(max_length=200)
    talk_summary = models.TextField(help_text='What is the idea worth spreading?')
    previous_experience = models.TextField(blank=True)
    linkedin = models.URLField(blank=True)
    video_url = models.URLField(
        blank=True,
        help_text='Optional link to a previous talk or an audition video.',
    )

    class Meta(SubmissionModel.Meta):
        verbose_name = 'Speaker Application'
        verbose_name_plural = 'Speaker Applications'

    def __str__(self):
        return f'{self.full_name} — {self.talk_title}'


class VolunteerApplication(SubmissionModel):
    """A volunteer/team application submitted through the Apply page."""

    class AvailabilityChoices(models.TextChoices):
        EVENT_DAY = 'event_day', 'Event Day Only'
        PART_TIME = 'part_time', 'Part Time (Year Round)'
        FULL_TIME = 'full_time', 'Full Time (Year Round)'

    full_name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=30, blank=True)
    university = models.CharField(max_length=200, blank=True)
    student_id = models.CharField(max_length=50, blank=True)
    preferred_department = models.CharField(
        max_length=100,
        blank=True,
        help_text='Free text — e.g. Marketing, Operations, Design.',
    )
    availability = models.CharField(
        max_length=20,
        choices=AvailabilityChoices.choices,
        default=AvailabilityChoices.EVENT_DAY,
    )
    skills = models.TextField(blank=True)
    motivation = models.TextField(help_text='Why do you want to join?')

    class Meta(SubmissionModel.Meta):
        verbose_name = 'Volunteer Application'
        verbose_name_plural = 'Volunteer Applications'

    def __str__(self):
        return f'{self.full_name} — {self.preferred_department or "Any department"}'


class PartnerApplication(SubmissionModel):
    """A sponsorship/partnership enquiry submitted through the Apply page."""

    class PartnershipTypeChoices(models.TextChoices):
        SPONSOR = 'sponsor', 'Sponsor'
        MEDIA = 'media', 'Media Partner'
        COMMUNITY = 'community', 'Community Partner'
        VENUE = 'venue', 'Venue Partner'
        OTHER = 'other', 'Other'

    organization_name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=30, blank=True)
    website = models.URLField(blank=True)
    partnership_type = models.CharField(
        max_length=20,
        choices=PartnershipTypeChoices.choices,
        default=PartnershipTypeChoices.SPONSOR,
    )
    interested_tier = models.ForeignKey(
        'sponsors.SponsorTier',
        related_name='partner_applications',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    proposal = models.TextField(help_text='What kind of partnership do you have in mind?')

    class Meta(SubmissionModel.Meta):
        verbose_name = 'Partner Application'
        verbose_name_plural = 'Partner Applications'

    def __str__(self):
        return f'{self.organization_name} — {self.get_partnership_type_display()}'
