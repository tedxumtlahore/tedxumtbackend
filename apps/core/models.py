"""
Core models - global site settings, hero, navigation, social links, FAQs.
These models power the public CMS surface for the website.
"""

from django.db import models

from apps.common.models import BaseModel


class SingletonModel(BaseModel):
    """
    Abstract base that ensures only one row exists.
    Used for global settings.
    """

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        return None

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class WebsiteSettings(SingletonModel):
    """Global site-wide settings. Only one row should ever exist."""

    # Organization identity
    site_name = models.CharField(max_length=100, default='TEDxUMT Lahore')
    tagline = models.CharField(max_length=200, default='Ideas Worth Spreading')
    description = models.TextField(
        default='An independently organized TED event at the University of Management and Technology.'
    )

    # Stats shown on homepage
    events_count = models.CharField(max_length=20, default='3')
    speakers_count = models.CharField(max_length=20, default='30+')
    attendees_count = models.CharField(max_length=20, default='4,200+')

    # About preview text on homepage
    about_summary = models.TextField(
        default=(
            'Founded in December 2025, TEDxUMT Lahore is the University of Management '
            'and Technology\'s first officially licensed TEDx organization. Inspired by '
            'Ideas Worth Spreading, we bring together innovators, creators, and '
            'changemakers to share ideas that inspire, connect, and create meaningful impact.'
        )
    )

    # Contact information
    email = models.EmailField(default='tedxumtlahore@umt.edu.pk')
    phone = models.CharField(max_length=30, blank=True)
    address = models.CharField(max_length=300, default='UMT Campus, C-II, Johar Town, Lahore')
    map_embed_url = models.URLField(blank=True)

    # Footer
    copyright_text = models.CharField(
        max_length=300,
        default='This independent TEDx event is operated under license from TED.'
    )
    footer_tagline = models.CharField(
        max_length=300,
        default="Bringing ideas worth spreading to Lahore's brightest minds since 2025."
    )

    # TED official listing
    ted_event_url = models.URLField(
        default='https://www.ted.com/tedx/events/69864',
        blank=True,
    )

    class Meta:
        verbose_name = 'Website Settings'
        verbose_name_plural = 'Website Settings'
        ordering = ['-created_at']

    def __str__(self):
        return 'Website Settings'


class HeroSection(SingletonModel):
    """Homepage hero section content."""

    eyebrow = models.CharField(
        max_length=200,
        default='TEDxUMT Lahore \u00a0\u00b7\u00a0 University of Management and Technology',
    )
    headline_line1 = models.CharField(max_length=100, default='Ideas worth')
    headline_line2 = models.CharField(max_length=100, default='spreading.')
    subheading = models.TextField(
        default=(
            "An independently organized TED event bringing Lahore\u2019s boldest thinkers, "
            'builders, and storytellers to one stage.'
        )
    )
    cta_primary_label = models.CharField(max_length=50, default='Register')
    cta_primary_url = models.CharField(max_length=200, default='/apply')
    cta_secondary_label = models.CharField(max_length=50, default='Become a Speaker')
    cta_secondary_url = models.CharField(max_length=200, default='/apply')

    # Background image — replaces the hardcoded local campus image
    background_image = models.ImageField(
        upload_to='hero/',
        blank=True,
        help_text='Recommended: 1920×1080px or wider. Replaces the campus background.',
    )

    class Meta:
        verbose_name = 'Hero Section'
        verbose_name_plural = 'Hero Section'
        ordering = ['-created_at']

    def __str__(self):
        return 'Hero Section'


class NavigationItem(BaseModel):
    """Navbar links — orderable, toggleable."""

    label = models.CharField(max_length=50)
    url = models.CharField(max_length=200)
    order = models.PositiveSmallIntegerField(default=0)
    is_visible = models.BooleanField(default=True)
    open_in_new_tab = models.BooleanField(default=False)

    class Meta:
        ordering = ['order', 'label']
        verbose_name = 'Navigation Item'
        verbose_name_plural = 'Navigation Items'

    def __str__(self):
        return self.label


class SocialLink(BaseModel):
    """Social media links shown in footer and speaker profiles."""

    class PlatformChoices(models.TextChoices):
        INSTAGRAM = 'instagram', 'Instagram'
        LINKEDIN = 'linkedin', 'LinkedIn'
        FACEBOOK = 'facebook', 'Facebook'
        YOUTUBE = 'youtube', 'YouTube'
        TWITTER = 'twitter', 'Twitter / X'
        TIKTOK = 'tiktok', 'TikTok'
        WEBSITE = 'website', 'Website'

    platform = models.CharField(max_length=20, choices=PlatformChoices.choices)
    url = models.URLField()
    display_label = models.CharField(
        max_length=10,
        help_text='Short label shown in footer badge (e.g. IG, in, FB, YT)',
    )
    aria_label = models.CharField(max_length=50, blank=True)
    order = models.PositiveSmallIntegerField(default=0)
    is_visible = models.BooleanField(default=True)

    class Meta:
        ordering = ['order', 'platform']
        verbose_name = 'Social Link'
        verbose_name_plural = 'Social Links'

    def __str__(self):
        return f'{self.get_platform_display()} — {self.url}'


class FAQ(BaseModel):
    """Frequently asked questions shown on the Contact page."""

    question = models.CharField(max_length=500)
    answer = models.TextField()
    order = models.PositiveSmallIntegerField(default=0)
    is_visible = models.BooleanField(default=True)

    class Meta:
        ordering = ['order', 'question']
        verbose_name = 'FAQ'
        verbose_name_plural = 'FAQs'

    def __str__(self):
        return self.question[:80]
