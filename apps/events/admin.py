from django.contrib import admin
from django.utils.html import format_html

from .models import Venue, Event, EventScheduleItem


@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = ['name', 'city', 'updated_at']
    search_fields = ['name', 'address', 'city']
    list_filter = ['city', 'is_active']
    ordering = ['name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['title', 'event_type', 'status', 'venue', 'start_datetime', 'is_featured', 'updated_at']
    list_editable = ['status', 'is_featured']
    list_display_links = ['title']
    search_fields = ['title', 'slug', 'short_description', 'description', 'venue__name', 'venue__city']
    list_filter = ['event_type', 'status', 'is_featured', 'venue', 'is_active']
    list_select_related = ['venue']
    ordering = ['-start_datetime', 'title']
    readonly_fields = ['slug', 'featured_image_preview', 'banner_image_preview', 'created_at', 'updated_at']

    fieldsets = (
        ('Event Details', {
            'fields': (
                'title', 'slug', 'short_description', 'description', 'venue', 'start_datetime', 'end_datetime',
                'registration_url', 'max_attendees', 'event_type', 'status', 'is_featured',
            ),
        }),
        # Without this block none of the ticketing fields render on the form,
        # so `registration_enabled` — which defaults to False — can never be
        # ticked, and every event reports "Registration for this event has not
        # opened yet." with no way for an organizer to change it.
        ('Ticketing', {
            'fields': (
                'registration_enabled',
                'ticket_price', 'currency', 'ticket_prefix',
                'registration_opens_at', 'registration_closes_at',
                'registration_hold_minutes',
            ),
            'description': (
                'Registration is closed until <b>registration enabled</b> is ticked. '
                'Capacity comes from <b>max attendees</b> above; leave it blank for '
                'unlimited. A ticket price of 0 issues free tickets instantly.'
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
    list_filter = ['event', 'speaker', 'is_active']
    list_select_related = ['event', 'speaker']
    ordering = ['event', 'start_time', 'title']
    readonly_fields = ['created_at', 'updated_at']
