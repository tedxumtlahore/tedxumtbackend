"""
Blog models - categories, tags, and posts.
"""

from django.db import models
from django.utils import timezone

from apps.common.models import BaseModel, StatusChoices
from apps.common.utils import generate_unique_slug


class Category(BaseModel):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, editable=False)
    description = models.TextField(blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(self, self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Tag(BaseModel):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(unique=True, editable=False)

    class Meta:
        ordering = ['name']
        verbose_name = 'Tag'
        verbose_name_plural = 'Tags'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(self, self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class BlogPost(BaseModel):
    title = models.CharField(max_length=250)
    slug = models.SlugField(unique=True, editable=False)
    excerpt = models.TextField(
        max_length=500,
        help_text='Short summary shown on cards and the blog index.',
    )
    content = models.TextField(help_text='Full article body.')
    category = models.ForeignKey(
        Category,
        related_name='posts',
        on_delete=models.PROTECT,
    )
    tags = models.ManyToManyField(Tag, related_name='posts', blank=True)
    cover_image = models.ImageField(upload_to='blog/', blank=True)
    author_name = models.CharField(max_length=150, default='TEDxUMT Lahore Team')
    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.DRAFT,
    )
    published_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Set automatically the first time the post is published.',
    )
    is_featured = models.BooleanField(
        default=False,
        help_text='Featured posts get the large hero card on the blog index.',
    )
    reading_minutes = models.PositiveSmallIntegerField(
        default=0,
        help_text='Leave at 0 to estimate automatically from the content length.',
    )

    class Meta:
        ordering = ['-published_at', '-created_at']
        verbose_name = 'Blog Post'
        verbose_name_plural = 'Blog Posts'
        indexes = [
            models.Index(fields=['status', '-published_at']),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(self, self.title)
        if self.status == StatusChoices.PUBLISHED and self.published_at is None:
            self.published_at = timezone.now()
        if not self.reading_minutes:
            self.reading_minutes = self.estimate_reading_minutes()
        super().save(*args, **kwargs)

    def estimate_reading_minutes(self):
        words = len((self.content or '').split())
        return max(1, round(words / 200)) if words else 1

    @property
    def is_published(self):
        return self.status == StatusChoices.PUBLISHED

    def __str__(self):
        return self.title
