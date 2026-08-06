"""
Sponsors models - sponsorship tiers and the sponsors within them.
"""

from django.db import models

from apps.common.models import BaseModel
from apps.common.utils import generate_unique_slug


class SponsorTier(BaseModel):
    """A sponsorship package (Title, Gold, Silver, ...)."""

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, editable=False)
    description = models.TextField(
        blank=True,
        help_text='What this package includes — shown on the Sponsors page.',
    )
    benefits = models.TextField(
        blank=True,
        help_text='One benefit per line. Rendered as a list on the website.',
    )
    order = models.PositiveSmallIntegerField(
        default=0,
        help_text='Lower numbers rank higher (Title = 0, Gold = 1, ...).',
    )
    is_visible = models.BooleanField(default=True)

    class Meta:
        ordering = ['order', 'name']
        verbose_name = 'Sponsor Tier'
        verbose_name_plural = 'Sponsor Tiers'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(self, self.name)
        super().save(*args, **kwargs)

    @property
    def benefit_list(self):
        return [line.strip() for line in (self.benefits or '').splitlines() if line.strip()]

    def __str__(self):
        return self.name


class Sponsor(BaseModel):
    """An organization sponsoring the event."""

    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, editable=False)
    tier = models.ForeignKey(SponsorTier, related_name='sponsors', on_delete=models.PROTECT)
    logo = models.ImageField(
        upload_to='sponsors/',
        blank=True,
        help_text='Transparent PNG or SVG works best. Falls back to the name in text.',
    )
    website = models.URLField(blank=True)
    description = models.TextField(blank=True)
    event = models.ForeignKey(
        'events.Event',
        related_name='sponsors',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text='Optional — which edition this organization sponsored.',
    )
    order = models.PositiveSmallIntegerField(default=0)
    is_visible = models.BooleanField(default=True)

    class Meta:
        ordering = ['tier__order', 'order', 'name']
        verbose_name = 'Sponsor'
        verbose_name_plural = 'Sponsors'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(self, self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.name} ({self.tier.name})'
