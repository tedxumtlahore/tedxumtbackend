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
    President or Organizer message — shown on About page.

    The founder briefly lived here as a fourth type. They have their own model
    now (see `Founder`), because a message is a quote attached to a role while
    the founder page is a profile.
    """

    class MessageTypeChoices(models.TextChoices):
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
        verbose_name_plural = 'Messages (President / Organizer)'

    def __str__(self):
        return f'{self.person_name} — {self.get_message_type_display()}'


class Founder(BaseModel):
    """
    The Founder page — a singleton, like HeroSection.

    Split out of `Message` once the founder got a page of their own. A message
    is a quote attached to a role; this is a profile, and it wants fields a
    quote does not: a story rather than a body, and somewhere to link.

    Nothing enforces a single row at the database level — the admin hides the
    add button once one exists, and the API serves the first visible row, which
    is the same shape of guarantee HeroSection makes.
    """

    name = models.CharField(max_length=200)
    role_title = models.CharField(
        max_length=200,
        default='Founder · TEDxUMT Lahore',
        help_text='Shown under the name, e.g. Founder & Licensee · TEDxUMT Lahore',
    )
    photo = models.ImageField(
        upload_to='founder/',
        blank=True,
        help_text='Portrait. A tall crop works best — it sits beside the story.',
    )
    story = models.TextField(
        help_text='The founder\u2019s story. Leave a blank line between paragraphs.',
    )
    email = models.EmailField(blank=True)
    linkedin = models.URLField(blank=True)
    instagram = models.URLField(blank=True)
    is_visible = models.BooleanField(
        default=True,
        help_text='Untick to hide the Founder page without deleting anything.',
    )

    class Meta:
        # Singular plural name: the changelist header should read "Founder",
        # not "Founders", because there is only ever one.
        verbose_name = 'Founder'
        verbose_name_plural = 'Founder'
        ordering = ['-updated_at']

    def __str__(self):
        return self.name
