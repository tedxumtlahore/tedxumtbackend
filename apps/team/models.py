"""
Team models - organizing committee departments and their members.
"""

from django.db import models

from apps.common.models import BaseModel
from apps.common.utils import generate_unique_slug


class Department(BaseModel):
    """A committee/department the organizing team is split into."""

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, editable=False)
    description = models.TextField(blank=True)
    order = models.PositiveSmallIntegerField(
        default=0,
        help_text='Lower numbers appear first on the Team page.',
    )
    is_visible = models.BooleanField(default=True)

    class Meta:
        ordering = ['order', 'name']
        verbose_name = 'Department'
        verbose_name_plural = 'Departments'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(self, self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class TeamMember(BaseModel):
    """A person on the organizing committee."""

    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, editable=False)
    role = models.CharField(max_length=200, help_text='e.g. President, Marketing Lead')
    department = models.ForeignKey(
        Department,
        related_name='members',
        on_delete=models.PROTECT,
    )
    photo = models.ImageField(upload_to='team/', blank=True)
    bio = models.TextField(blank=True)
    email = models.EmailField(blank=True)
    linkedin = models.URLField(blank=True)
    instagram = models.URLField(blank=True)
    order = models.PositiveSmallIntegerField(
        default=0,
        help_text='Lower numbers appear first within the department.',
    )
    is_visible = models.BooleanField(default=True)

    class Meta:
        ordering = ['department__order', 'order', 'name']
        verbose_name = 'Team Member'
        verbose_name_plural = 'Team Members'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(self, self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.name} — {self.role}'
