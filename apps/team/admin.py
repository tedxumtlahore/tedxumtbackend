from django.contrib import admin
from django.utils.html import format_html

from .models import Department, TeamMember


class TeamMemberInline(admin.TabularInline):
    model = TeamMember
    extra = 0
    fields = ['name', 'role', 'photo', 'order', 'is_visible']
    ordering = ['order', 'name']
    show_change_link = True


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'order', 'member_count', 'is_visible', 'updated_at']
    list_editable = ['order', 'is_visible']
    list_display_links = ['name']
    search_fields = ['name', 'description']
    list_filter = ['is_visible', 'is_active']
    ordering = ['order', 'name']
    readonly_fields = ['slug', 'created_at', 'updated_at']
    inlines = [TeamMemberInline]

    fieldsets = (
        ('Department', {
            'fields': ('name', 'slug', 'description', 'order', 'is_visible'),
        }),
        ('System', {
            'fields': ('is_active', 'created_at', 'updated_at'),
        }),
    )

    @admin.display(description='Members')
    def member_count(self, obj):
        return obj.members.count()


@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = ['name', 'role', 'department', 'order', 'is_visible', 'updated_at']
    list_editable = ['order', 'is_visible']
    list_display_links = ['name']
    search_fields = ['name', 'role', 'bio', 'email', 'department__name']
    list_filter = ['department', 'is_visible', 'is_active']
    list_select_related = ['department']
    ordering = ['department__order', 'order', 'name']
    readonly_fields = ['slug', 'photo_preview', 'created_at', 'updated_at']

    fieldsets = (
        ('Member', {
            'fields': ('name', 'slug', 'role', 'department', 'bio', 'order', 'is_visible'),
        }),
        ('Photo', {
            'fields': ('photo', 'photo_preview'),
        }),
        ('Contact & Social', {
            'fields': ('email', 'linkedin', 'instagram'),
        }),
        ('System', {
            'fields': ('is_active', 'created_at', 'updated_at'),
        }),
    )

    @admin.display(description='Preview')
    def photo_preview(self, obj):
        if obj.photo:
            return format_html('<img src="{}" style="max-height:120px;border-radius:6px" />', obj.photo.url)
        return '—'
