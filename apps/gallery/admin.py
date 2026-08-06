from django.contrib import admin
from django.utils.html import format_html

from .models import GalleryAlbum, GalleryImage


class GalleryImageInline(admin.TabularInline):
    model = GalleryImage
    extra = 1
    fields = ['image', 'thumbnail', 'caption', 'media_type', 'video_url', 'order', 'is_visible']
    readonly_fields = ['thumbnail']
    ordering = ['order']

    @admin.display(description='Thumb')
    def thumbnail(self, obj):
        if obj.pk and obj.image:
            return format_html('<img src="{}" style="max-height:70px;border-radius:4px" />', obj.image.url)
        return '—'


@admin.register(GalleryAlbum)
class GalleryAlbumAdmin(admin.ModelAdmin):
    list_display = ['title', 'event', 'image_count', 'order', 'is_visible', 'updated_at']
    list_editable = ['order', 'is_visible']
    list_display_links = ['title']
    search_fields = ['title', 'description', 'event__title']
    list_filter = ['is_visible', 'event', 'is_active']
    list_select_related = ['event']
    ordering = ['order', '-created_at']
    readonly_fields = ['slug', 'cover_preview', 'created_at', 'updated_at']
    inlines = [GalleryImageInline]

    fieldsets = (
        ('Album', {
            'fields': ('title', 'slug', 'description', 'event', 'order', 'is_visible'),
        }),
        ('Cover', {
            'fields': ('cover_image', 'cover_preview'),
        }),
        ('System', {
            'fields': ('is_active', 'created_at', 'updated_at'),
        }),
    )

    @admin.display(description='Images')
    def image_count(self, obj):
        return obj.images.count()

    @admin.display(description='Cover Preview')
    def cover_preview(self, obj):
        if obj.cover_image:
            return format_html('<img src="{}" style="max-height:140px;border-radius:6px" />', obj.cover_image.url)
        return '—'


@admin.register(GalleryImage)
class GalleryImageAdmin(admin.ModelAdmin):
    list_display = ['thumbnail', 'caption', 'album', 'media_type', 'order', 'is_visible', 'updated_at']
    list_editable = ['order', 'is_visible']
    list_display_links = ['thumbnail', 'caption']
    search_fields = ['caption', 'alt_text', 'album__title']
    list_filter = ['media_type', 'is_visible', 'album', 'is_active']
    list_select_related = ['album']
    ordering = ['album', 'order']
    readonly_fields = ['image_preview', 'created_at', 'updated_at']

    fieldsets = (
        ('Media', {
            'fields': ('album', 'image', 'image_preview', 'media_type', 'video_url'),
        }),
        ('Text', {
            'fields': ('caption', 'alt_text', 'order', 'is_visible'),
        }),
        ('System', {
            'fields': ('is_active', 'created_at', 'updated_at'),
        }),
    )

    @admin.display(description='Preview')
    def thumbnail(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height:60px;border-radius:4px" />', obj.image.url)
        return '—'

    @admin.display(description='Preview')
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height:200px;border-radius:6px" />', obj.image.url)
        return '—'
