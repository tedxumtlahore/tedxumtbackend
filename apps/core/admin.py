"""
Core admin - CMS panel for global settings, navigation, social links, FAQs.
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import WebsiteSettings, HeroSection, NavigationItem, SocialLink, FAQ


@admin.register(WebsiteSettings)
class WebsiteSettingsAdmin(admin.ModelAdmin):
    list_display = ['site_name', 'tagline', 'email', 'is_active', 'updated_at']
    search_fields = ['site_name', 'tagline', 'description', 'email', 'address']
    list_filter = ['is_active']
    ordering = ['-updated_at']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Organization Identity', {
            'fields': ('site_name', 'tagline', 'description'),
        }),
        ('Homepage Stats', {
            'fields': ('events_count', 'speakers_count', 'attendees_count'),
            'description': 'Numbers shown in the homepage About preview section.',
        }),
        ('About Preview Text', {
            'fields': ('about_summary',),
        }),
        ('Contact Information', {
            'fields': ('email', 'phone', 'address', 'map_embed_url'),
        }),
        ('Footer', {
            'fields': ('footer_tagline', 'copyright_text', 'ted_event_url'),
        }),
        ('System', {
            'fields': ('is_active', 'created_at', 'updated_at'),
        }),
    )

    def has_add_permission(self, request):
        return not WebsiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(HeroSection)
class HeroSectionAdmin(admin.ModelAdmin):
    list_display = ['eyebrow', 'headline_line1', 'headline_line2', 'is_active', 'updated_at']
    search_fields = ['eyebrow', 'headline_line1', 'headline_line2', 'subheading']
    list_filter = ['is_active']
    ordering = ['-updated_at']
    readonly_fields = ['image_preview', 'created_at', 'updated_at']
    fieldsets = (
        ('Headline', {
            'fields': ('eyebrow', 'headline_line1', 'headline_line2', 'subheading'),
        }),
        ('Call to Action Buttons', {
            'fields': (
                'cta_primary_label', 'cta_primary_url',
                'cta_secondary_label', 'cta_secondary_url',
            ),
        }),
        ('Background Image', {
            'fields': ('background_image', 'image_preview'),
            'description': 'Upload a full-width campus/event image. Recommended: 1920×1080px.',
        }),
        ('System', {
            'fields': ('is_active', 'created_at', 'updated_at'),
        }),
    )

    def image_preview(self, obj):
        if obj.background_image:
            return format_html('<img src="{}" style="max-height:120px;border-radius:6px"/>', obj.background_image.url)
        return '—'
    image_preview.short_description = 'Preview'

    def has_add_permission(self, request):
        return not HeroSection.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(NavigationItem)
class NavigationItemAdmin(admin.ModelAdmin):
    list_display = ['label', 'url', 'order', 'is_visible', 'open_in_new_tab', 'updated_at']
    list_editable = ['order', 'is_visible', 'open_in_new_tab']
    list_display_links = ['label']
    search_fields = ['label', 'url']
    list_filter = ['is_visible', 'open_in_new_tab']
    ordering = ['order', 'label']


@admin.register(SocialLink)
class SocialLinkAdmin(admin.ModelAdmin):
    list_display = ['platform', 'display_label', 'url', 'order', 'is_visible', 'updated_at']
    list_editable = ['order', 'is_visible']
    list_display_links = ['platform']
    search_fields = ['display_label', 'url', 'aria_label']
    list_filter = ['platform', 'is_visible']
    ordering = ['order', 'platform']


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ['question', 'order', 'is_visible', 'updated_at']
    list_editable = ['order', 'is_visible']
    list_display_links = ['question']
    search_fields = ['question', 'answer']
    list_filter = ['is_visible']
    ordering = ['order', 'question']
