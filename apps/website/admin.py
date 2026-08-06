from django.contrib import admin
from django.utils.html import format_html

from .models import AboutSection, CoreValue, Message


@admin.register(AboutSection)
class AboutSectionAdmin(admin.ModelAdmin):
    list_display = ['section_key', 'heading', 'order', 'is_visible', 'updated_at']
    list_editable = ['order', 'is_visible']
    list_display_links = ['section_key']
    search_fields = ['section_key', 'eyebrow', 'heading', 'body', 'external_link_label']
    list_filter = ['is_visible', 'section_key', 'image_position']
    ordering = ['order', 'section_key']
    readonly_fields = ['image_preview', 'created_at', 'updated_at']

    fieldsets = (
        ('Content', {
            'fields': (
                'section_key', 'eyebrow', 'heading', 'body', 'image', 'image_position',
                'external_link_label', 'external_link_url', 'order', 'is_visible',
            ),
        }),
        ('Preview', {
            'fields': ('image_preview',),
        }),
        ('System', {
            'fields': ('created_at', 'updated_at'),
        }),
    )

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height:120px;border-radius:6px" />', obj.image.url)
        return '—'

    image_preview.short_description = 'Preview'


@admin.register(CoreValue)
class CoreValueAdmin(admin.ModelAdmin):
    list_display = ['title', 'icon_key', 'order', 'updated_at']
    list_editable = ['order']
    list_display_links = ['title']
    search_fields = ['title', 'description', 'icon_key']
    list_filter = ['icon_key', 'is_active']
    ordering = ['order', 'title']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['person_name', 'message_type', 'order', 'is_visible', 'updated_at']
    list_editable = ['order', 'is_visible']
    list_display_links = ['person_name']
    search_fields = ['person_name', 'role_title', 'message_body']
    list_filter = ['message_type', 'is_visible', 'is_active']
    ordering = ['order', 'message_type']
    readonly_fields = ['photo_preview', 'created_at', 'updated_at']

    fieldsets = (
        ('Message', {
            'fields': ('message_type', 'person_name', 'role_title', 'message_body', 'photo', 'order', 'is_visible'),
        }),
        ('Preview', {
            'fields': ('photo_preview',),
        }),
        ('System', {
            'fields': ('created_at', 'updated_at'),
        }),
    )

    def photo_preview(self, obj):
        if obj.photo:
            return format_html('<img src="{}" style="max-height:120px;border-radius:6px" />', obj.photo.url)
        return '—'

    photo_preview.short_description = 'Preview'
