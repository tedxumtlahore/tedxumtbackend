from django.contrib import admin
from django.utils.html import format_html

from .models import Speaker


@admin.register(Speaker)
class SpeakerAdmin(admin.ModelAdmin):
    list_display = ['name', 'designation', 'organization', 'event', 'featured', 'updated_at']
    list_editable = ['featured']
    list_display_links = ['name']
    search_fields = ['name', 'designation', 'organization', 'talk_title', 'bio', 'event__title']
    list_filter = ['featured', 'event']
    ordering = ['-featured', 'name']
    readonly_fields = ['slug', 'profile_image_preview', 'created_at', 'updated_at']

    fieldsets = (
        ('Speaker Profile', {
            'fields': (
                'name', 'slug', 'designation', 'organization', 'bio', 'profile_image', 'profile_image_preview',
                'linkedin', 'instagram', 'website', 'talk_title', 'featured', 'event',
            ),
        }),
        ('System', {
            'fields': ('created_at', 'updated_at'),
        }),
    )

    def profile_image_preview(self, obj):
        if obj.profile_image:
            return format_html('<img src="{}" style="max-height:120px;border-radius:6px" />', obj.profile_image.url)
        return '—'

    profile_image_preview.short_description = 'Preview'
