"""
Website models — About page, Mission/Vision, Core Values, President/Organizer messages.
"""

from django.db import models


class AboutSection(models.Model):
    """
    Each row represents one visual section on the About page.
    The section_key matches the hardcoded sections in About.jsx.
    """

    SECTION_KEYS = [
        ('what_is_ted', 'What is TED?'),
        ('what_is_tedx', 'What is TEDx?'),
        ('our_story', 'Our Story'),
        ('mission', 'Our Mission'),
        ('vision', 'Our Vision'),
    ]

    IMAGE_POSITION = [
        ('left', 'Image on Left'),
        ('right', 'Image on Right'),
    ]

    section_key = models.CharField(max_length=30, choices=SECTION_KEYS, unique=True)
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
        choices=IMAGE_POSITION,
        default='right',
    )
    external_link_label = models.CharField(max_length=100, blank=True)
    external_link_url = models.URLField(blank=True)
    is_visible = models.BooleanField(default=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['order']
        verbose_name = 'About Section'
        verbose_name_plural = 'About Sections'

    def __str__(self):
        return self.get_section_key_display()


class CoreValue(models.Model):
    """Core values shown in the About page 'What We Stand For' grid."""

    ICON_CHOICES = [
        ('innovation', '⚡ Innovation'),
        ('curiosity', '🔍 Curiosity'),
        ('leadership', '★ Leadership'),
        ('collaboration', '∞ Collaboration'),
        ('creativity', '🎨 Creativity'),
        ('impact', '🌐 Community Impact'),
        ('mission', '◆ Mission'),
        ('vision', '○ Vision'),
    ]

    icon_key = models.CharField(max_length=20, choices=ICON_CHOICES)
    title = models.CharField(max_length=100)
    description = models.TextField()
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['order']
        verbose_name = 'Core Value'
        verbose_name_plural = 'Core Values'

    def __str__(self):
        return self.title


class Message(models.Model):
    """President or Organizer message — shown on About page."""

    TYPE_CHOICES = [
        ('president', 'President'),
        ('organizer', 'Organizer'),
        ('vice_president', 'Vice President'),
    ]

    message_type = models.CharField(max_length=20, choices=TYPE_CHOICES, unique=True)
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
        ordering = ['order']
        verbose_name = 'Message'
        verbose_name_plural = 'Messages (President / Organizer)'

    def __str__(self):
        return f'{self.person_name} — {self.get_message_type_display()}'
