from django.contrib import admin
from django.utils.html import format_html

from apps.common.models import StatusChoices

from .models import BlogPost, Category, Tag


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'order', 'post_count', 'is_active', 'updated_at']
    list_editable = ['order']
    list_display_links = ['name']
    search_fields = ['name', 'description']
    list_filter = ['is_active']
    ordering = ['order', 'name']
    readonly_fields = ['slug', 'created_at', 'updated_at']

    @admin.display(description='Posts')
    def post_count(self, obj):
        return obj.posts.count()


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name', 'post_count', 'is_active', 'updated_at']
    search_fields = ['name']
    list_filter = ['is_active']
    ordering = ['name']
    readonly_fields = ['slug', 'created_at', 'updated_at']

    @admin.display(description='Posts')
    def post_count(self, obj):
        return obj.posts.count()


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'status', 'is_featured', 'published_at', 'updated_at']
    list_editable = ['status', 'is_featured']
    list_display_links = ['title']
    search_fields = ['title', 'excerpt', 'content', 'author_name', 'category__name']
    list_filter = ['status', 'is_featured', 'category', 'tags', 'is_active']
    list_select_related = ['category']
    filter_horizontal = ['tags']
    date_hierarchy = 'created_at'
    ordering = ['-published_at', '-created_at']
    readonly_fields = ['slug', 'cover_preview', 'reading_minutes', 'created_at', 'updated_at']
    actions = ['publish_posts', 'unpublish_posts']

    fieldsets = (
        ('Article', {
            'fields': ('title', 'slug', 'excerpt', 'content'),
        }),
        ('Classification', {
            'fields': ('category', 'tags', 'author_name'),
        }),
        ('Cover Image', {
            'fields': ('cover_image', 'cover_preview'),
        }),
        ('Publishing', {
            'fields': ('status', 'published_at', 'is_featured', 'reading_minutes'),
            'description': 'Publishing a draft stamps the publish date automatically.',
        }),
        ('System', {
            'fields': ('is_active', 'created_at', 'updated_at'),
        }),
    )

    @admin.display(description='Cover Preview')
    def cover_preview(self, obj):
        if obj.cover_image:
            return format_html('<img src="{}" style="max-height:160px;border-radius:6px" />', obj.cover_image.url)
        return '—'

    @admin.action(description='Publish selected posts')
    def publish_posts(self, request, queryset):
        updated = 0
        for post in queryset:
            post.status = StatusChoices.PUBLISHED
            post.save()
            updated += 1
        self.message_user(request, f'{updated} post(s) published.')

    @admin.action(description='Move selected posts back to draft')
    def unpublish_posts(self, request, queryset):
        updated = queryset.update(status=StatusChoices.DRAFT)
        self.message_user(request, f'{updated} post(s) moved to draft.')
