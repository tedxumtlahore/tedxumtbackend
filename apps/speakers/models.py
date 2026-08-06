"""
Speakers models - public speaker profiles linked to events.
"""

from django.db import models

from apps.common.models import BaseModel
from apps.common.utils import generate_unique_slug


class Speaker(BaseModel):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, editable=False)
    designation = models.CharField(max_length=200)
    organization = models.CharField(max_length=200)
    bio = models.TextField()
    profile_image = models.ImageField(upload_to='speakers/profiles/', blank=True)
    linkedin = models.URLField(blank=True)
    instagram = models.URLField(blank=True)
    website = models.URLField(blank=True)
    talk_title = models.CharField(max_length=200)
    featured = models.BooleanField(default=False)
    event = models.ForeignKey(
        'events.Event',
        related_name='speakers',
        on_delete=models.PROTECT,
    )

    class Meta:
        ordering = ['-featured', 'name']
        verbose_name = 'Speaker'
        verbose_name_plural = 'Speakers'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(self, self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
