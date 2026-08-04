from django.contrib import admin
from django.utils.html import format_html

from .models import Venue, Event, EventScheduleItem


@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = ['name', 'city', 'updated_at']
    search_fields = ['name', 'address', 'city']
    list_filter = ['city']
    ordering = ['name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['title', 'event_type', 'status', 'venue', 'start_datetime', 'is_featured', 'updated_at']
    list_editable = ['status', 'is_featured']
    list_display_links = ['title']
    search_fields = ['title', 'slug', 'short_description', 'description', 'venue__name', 'venue__city']
    list_filter = ['event_type', 'status', 'is_featured', 'venue']
    ordering = ['-start_datetime', 'title']
    readonly_fields = ['slug', 'featured_image_preview', 'banner_image_preview', 'created_at', 'updated_at']

    fieldsets = (
        ('Event Details', {
            'fields': (
                'title', 'slug', 'short_description', 'description', 'venue', 'start_datetime', 'end_datetime',
                'registration_url', 'max_attendees', 'event_type', 'status', 'is_featured',
            ),
        }),
        ('Media', {
            'fields': ('featured_image', 'featured_image_preview', 'banner_image', 'banner_image_preview'),
        }),
        ('System', {
            'fields': ('is_active', 'created_at', 'updated_at'),
        }),
    )

    def featured_image_preview(self, obj):
        if obj.featured_image:
            return format_html('<img src="{}" style="max-height:120px;border-radius:6px" />', obj.featured_image.url)
        return '—'

    featured_image_preview.short_description = 'Featured Image Preview'

    def banner_image_preview(self, obj):
        if obj.banner_image:
            return format_html('<img src="{}" style="max-height:120px;border-radius:6px" />', obj.banner_image.url)
        return '—'

    banner_image_preview.short_description = 'Banner Image Preview'


@admin.register(EventScheduleItem)
class EventScheduleItemAdmin(admin.ModelAdmin):
    list_display = ['event', 'title', 'speaker', 'start_time', 'end_time', 'updated_at']
    search_fields = ['title', 'description', 'event__title', 'speaker__name']
    list_filter = ['event']
    ordering = ['event', 'start_time', 'title']
    readonly_fields = ['created_at', 'updated_at']
