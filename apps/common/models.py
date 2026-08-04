from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ['-created_at']


class ActiveModel(models.Model):
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True


class BaseModel(TimeStampedModel, ActiveModel):
    class Meta:
        abstract = True
        ordering = ['-created_at']


class StatusChoices(models.TextChoices):
    DRAFT = 'draft', 'Draft'
    REVIEW = 'review', 'Review'
    PUBLISHED = 'published', 'Published'
    ARCHIVED = 'archived', 'Archived'
