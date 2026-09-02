"""
Website models - About page, mission/vision, core values, and leadership messages.
"""

from django.db import models

from apps.common.models import BaseModel


class AboutSection(BaseModel):
    """
    Each row represents one visual section on the About page.
    The section_key matches the hardcoded sections in About.jsx.
    """

    class SectionKeyChoices(models.TextChoices):
        WHAT_IS_TED = 'what_is_ted', 'What is TED?'
        WHAT_IS_TEDX = 'what_is_tedx', 'What is TEDx?'
        OUR_STORY = 'our_story', 'Our Story'
        MISSION = 'mission', 'Our Mission'
        VISION = 'vision', 'Our Vision'

    class ImagePositionChoices(models.TextChoices):
        LEFT = 'left', 'Image on Left'
        RIGHT = 'right', 'Image on Right'

    section_key = models.CharField(max_length=30, choices=SectionKeyChoices.choices, unique=True)
    eyebrow = models.CharField(max_length=100, blank=True)
    heading = models.CharField(max_length=300)
    body = models.TextField()
    image = models.ImageField(
        upload_to='about/',
        blank=True,
        help_text='Section image. Will be displayed beside the text.',
    )
    image_position = models.CharField(
        max_length=10,
        choices=ImagePositionChoices.choices,
        default=ImagePositionChoices.RIGHT,
    )
    external_link_label = models.CharField(max_length=100, blank=True)
    external_link_url = models.URLField(blank=True)
    is_visible = models.BooleanField(default=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['order', 'section_key']
        verbose_name = 'About Section'
        verbose_name_plural = 'About Sections'

    def __str__(self):
        return self.get_section_key_display()


class CoreValue(BaseModel):
    """Core values shown in the About page 'What We Stand For' grid."""

    class IconChoices(models.TextChoices):
        INNOVATION = 'innovation', 'Innovation'
        CURIOSITY = 'curiosity', 'Curiosity'
        LEADERSHIP = 'leadership', 'Leadership'
        COLLABORATION = 'collaboration', 'Collaboration'
        CREATIVITY = 'creativity', 'Creativity'
        IMPACT = 'impact', 'Community Impact'
        MISSION = 'mission', 'Mission'
        VISION = 'vision', 'Vision'

    icon_key = models.CharField(max_length=20, choices=IconChoices.choices)
    title = models.CharField(max_length=100)
    description = models.TextField()
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['order', 'title']
        verbose_name = 'Core Value'
        verbose_name_plural = 'Core Values'

    def __str__(self):
        return self.title


class Message(BaseModel):
    """
    A named person, their role, a portrait and something they wrote.

    Originally just the President/Organizer notes on the About page. The
    `founder` type reuses the same shape for the dedicated Founder page — the
    fields wanted there (name, title, photo, long-form text) are exactly these,
    so it needs no second model, no new admin and no new endpoint. Because
    `message_type` is unique there is at most one founder, which is the point.
    """

    class MessageTypeChoices(models.TextChoices):
        FOUNDER = 'founder', 'Founder'
        PRESIDENT = 'president', 'President'
        ORGANIZER = 'organizer', 'Organizer'
        VICE_PRESIDENT = 'vice_president', 'Vice President'

    message_type = models.CharField(max_length=20, choices=MessageTypeChoices.choices, unique=True)
    person_name = models.CharField(max_length=200)
    role_title = models.CharField(
        max_length=200,
        help_text='e.g. President & Official Organizer · TEDxUMT Lahore',
    )
    message_body = models.TextField()
    photo = models.ImageField(
        upload_to='messages/',
        blank=True,
        help_text='Portrait photo. Will appear beside the quote.',
    )
    is_visible = models.BooleanField(default=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['order', 'message_type']
        verbose_name = 'Message'
        verbose_name_plural = 'Messages (Founder / President / Organizer)'

    def __str__(self):
        return f'{self.person_name} — {self.get_message_type_display()}'
