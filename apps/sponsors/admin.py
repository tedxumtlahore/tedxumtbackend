from django.contrib import admin
from django.utils.html import format_html

from .models import Sponsor, SponsorTier


class SponsorInline(admin.TabularInline):
    model = Sponsor
    extra = 0
    fields = ['name', 'logo', 'website', 'order', 'is_visible']
    ordering = ['order', 'name']
    show_change_link = True


@admin.register(SponsorTier)
class SponsorTierAdmin(admin.ModelAdmin):
    list_display = ['name', 'order', 'sponsor_count', 'is_visible', 'updated_at']
    list_editable = ['order', 'is_visible']
    list_display_links = ['name']
    search_fields = ['name', 'description', 'benefits']
    list_filter = ['is_visible', 'is_active']
    ordering = ['order', 'name']
    readonly_fields = ['slug', 'created_at', 'updated_at']
    inlines = [SponsorInline]

    fieldsets = (
        ('Tier', {
            'fields': ('name', 'slug', 'description', 'order', 'is_visible'),
        }),
        ('Benefits', {
            'fields': ('benefits',),
            'description': 'One benefit per line — the website renders these as a bullet list.',
        }),
        ('System', {
            'fields': ('is_active', 'created_at', 'updated_at'),
        }),
    )

    @admin.display(description='Sponsors')
    def sponsor_count(self, obj):
        return obj.sponsors.count()


@admin.register(Sponsor)
class SponsorAdmin(admin.ModelAdmin):
    list_display = ['name', 'tier', 'event', 'order', 'is_visible', 'updated_at']
    list_editable = ['order', 'is_visible']
    list_display_links = ['name']
    search_fields = ['name', 'description', 'website', 'tier__name']
    list_filter = ['tier', 'event', 'is_visible', 'is_active']
    list_select_related = ['tier', 'event']
    ordering = ['tier__order', 'order', 'name']
    readonly_fields = ['slug', 'logo_preview', 'created_at', 'updated_at']

    fieldsets = (
        ('Sponsor', {
            'fields': ('name', 'slug', 'tier', 'event', 'description', 'website', 'order', 'is_visible'),
        }),
        ('Logo', {
            'fields': ('logo', 'logo_preview'),
        }),
        ('System', {
            'fields': ('is_active', 'created_at', 'updated_at'),
        }),
    )

    @admin.display(description='Logo Preview')
    def logo_preview(self, obj):
        if obj.logo:
            return format_html(
                '<img src="{}" style="max-height:90px;background:#fff;padding:6px;border-radius:6px" />',
                obj.logo.url,
            )
        return '—'
