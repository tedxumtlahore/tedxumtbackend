"""
Gallery models - albums of photos, videos, and behind-the-scenes media.
"""

from django.db import models

from apps.common.models import BaseModel
from apps.common.utils import generate_unique_slug
from apps.common.validators import validate_http_url


class GalleryAlbum(BaseModel):
    """A collection of media, usually tied to one event."""

    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, editable=False)
    description = models.TextField(blank=True)
    event = models.ForeignKey(
        'events.Event',
        related_name='gallery_albums',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text='Optional — link this album to an event.',
    )
    cover_image = models.ImageField(upload_to='gallery/covers/', blank=True)
    order = models.PositiveSmallIntegerField(default=0)
    is_visible = models.BooleanField(default=True)

    class Meta:
        ordering = ['order', '-created_at', 'title']
        verbose_name = 'Gallery Album'
        verbose_name_plural = 'Gallery Albums'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(self, self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class GalleryImage(BaseModel):
    """One media item inside an album."""

    class MediaTypeChoices(models.TextChoices):
        PHOTO = 'photo', 'Photo'
        VIDEO = 'video', 'Video'
        BTS = 'bts', 'Behind the Scenes'

    album = models.ForeignKey(GalleryAlbum, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='gallery/images/')
    caption = models.CharField(max_length=300, blank=True)
    alt_text = models.CharField(
        max_length=200,
        blank=True,
        help_text='Description for screen readers. Falls back to the caption.',
    )
    media_type = models.CharField(
        max_length=10,
        choices=MediaTypeChoices.choices,
        default=MediaTypeChoices.PHOTO,
    )
    video_url = models.URLField(
        blank=True,
        validators=[validate_http_url],
        help_text='For video items — the YouTube/Vimeo link. The image acts as the thumbnail.',
    )
    order = models.PositiveSmallIntegerField(default=0)
    is_visible = models.BooleanField(default=True)

    class Meta:
        ordering = ['album', 'order', '-created_at']
        verbose_name = 'Gallery Image'
        verbose_name_plural = 'Gallery Images'

    def __str__(self):
        return self.caption or f'{self.album.title} #{self.pk}'
