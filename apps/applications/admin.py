"""
Applications admin - the organizers' inbox.

Submissions are never created by hand here, only triaged, so add permission
is disabled and the submitted fields are read-only.
"""

from django.contrib import admin
from django.utils import timezone

from .models import (
    ContactMessage,
    NewsletterSubscriber,
    PartnerApplication,
    SpeakerApplication,
    SubmissionStatusChoices,
    VolunteerApplication,
)


class ReadOnlySubmissionAdmin(admin.ModelAdmin):
    """Base admin for submitted forms: triage only, no hand-authoring."""

    submitted_fields = []
    actions = ['mark_in_review', 'mark_accepted', 'mark_rejected', 'mark_archived']
    list_filter = ['status', 'created_at']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']

    def get_readonly_fields(self, request, obj=None):
        return list(self.submitted_fields) + ['submitted_ip', 'created_at', 'updated_at']

    def has_add_permission(self, request):
        return False

    @admin.action(description='Mark selected as In Review')
    def mark_in_review(self, request, queryset):
        count = queryset.update(status=SubmissionStatusChoices.IN_REVIEW)
        self.message_user(request, f'{count} submission(s) moved to In Review.')

    @admin.action(description='Mark selected as Accepted')
    def mark_accepted(self, request, queryset):
        count = queryset.update(status=SubmissionStatusChoices.ACCEPTED)
        self.message_user(request, f'{count} submission(s) accepted.')

    @admin.action(description='Mark selected as Rejected')
    def mark_rejected(self, request, queryset):
        count = queryset.update(status=SubmissionStatusChoices.REJECTED)
        self.message_user(request, f'{count} submission(s) rejected.')

    @admin.action(description='Archive selected')
    def mark_archived(self, request, queryset):
        count = queryset.update(status=SubmissionStatusChoices.ARCHIVED)
        self.message_user(request, f'{count} submission(s) archived.')


@admin.register(ContactMessage)
class ContactMessageAdmin(ReadOnlySubmissionAdmin):
    submitted_fields = ['name', 'email', 'subject', 'message']
    list_display = ['subject', 'name', 'email', 'status', 'is_read', 'created_at']
    list_editable = ['status', 'is_read']
    list_display_links = ['subject']
    search_fields = ['name', 'email', 'subject', 'message']
    list_filter = ['status', 'is_read', 'created_at']
    actions = ReadOnlySubmissionAdmin.actions + ['mark_as_read']

    fieldsets = (
        ('Message', {'fields': ('name', 'email', 'subject', 'message')}),
        ('Triage', {'fields': ('status', 'is_read', 'internal_notes')}),
        ('System', {'fields': ('submitted_ip', 'is_active', 'created_at', 'updated_at')}),
    )

    @admin.action(description='Mark selected as read')
    def mark_as_read(self, request, queryset):
        count = queryset.update(is_read=True)
        self.message_user(request, f'{count} message(s) marked as read.')


@admin.register(SpeakerApplication)
class SpeakerApplicationAdmin(ReadOnlySubmissionAdmin):
    submitted_fields = [
        'full_name', 'email', 'phone', 'organization', 'designation',
        'talk_title', 'talk_summary', 'previous_experience', 'linkedin', 'video_url',
    ]
    list_display = ['full_name', 'talk_title', 'organization', 'email', 'status', 'created_at']
    list_editable = ['status']
    list_display_links = ['full_name']
    search_fields = ['full_name', 'email', 'talk_title', 'talk_summary', 'organization']

    fieldsets = (
        ('Applicant', {'fields': ('full_name', 'email', 'phone', 'organization', 'designation', 'linkedin')}),
        ('The Talk', {'fields': ('talk_title', 'talk_summary', 'previous_experience', 'video_url')}),
        ('Triage', {'fields': ('status', 'internal_notes')}),
        ('System', {'fields': ('submitted_ip', 'is_active', 'created_at', 'updated_at')}),
    )


@admin.register(VolunteerApplication)
class VolunteerApplicationAdmin(ReadOnlySubmissionAdmin):
    submitted_fields = [
        'full_name', 'email', 'phone', 'university', 'student_id',
        'preferred_department', 'availability', 'skills', 'motivation',
    ]
    list_display = ['full_name', 'preferred_department', 'availability', 'email', 'status', 'created_at']
    list_editable = ['status']
    list_display_links = ['full_name']
    search_fields = ['full_name', 'email', 'university', 'preferred_department', 'skills']
    list_filter = ['status', 'availability', 'created_at']

    fieldsets = (
        ('Applicant', {'fields': ('full_name', 'email', 'phone', 'university', 'student_id')}),
        ('Application', {'fields': ('preferred_department', 'availability', 'skills', 'motivation')}),
        ('Triage', {'fields': ('status', 'internal_notes')}),
        ('System', {'fields': ('submitted_ip', 'is_active', 'created_at', 'updated_at')}),
    )


@admin.register(PartnerApplication)
class PartnerApplicationAdmin(ReadOnlySubmissionAdmin):
    submitted_fields = [
        'organization_name', 'contact_person', 'email', 'phone', 'website',
        'partnership_type', 'interested_tier', 'proposal',
    ]
    list_display = [
        'organization_name', 'contact_person', 'partnership_type',
        'interested_tier', 'status', 'created_at',
    ]
    list_editable = ['status']
    list_display_links = ['organization_name']
    search_fields = ['organization_name', 'contact_person', 'email', 'proposal']
    list_filter = ['status', 'partnership_type', 'interested_tier', 'created_at']
    list_select_related = ['interested_tier']

    fieldsets = (
        ('Organization', {'fields': ('organization_name', 'contact_person', 'email', 'phone', 'website')}),
        ('Proposal', {'fields': ('partnership_type', 'interested_tier', 'proposal')}),
        ('Triage', {'fields': ('status', 'internal_notes')}),
        ('System', {'fields': ('submitted_ip', 'is_active', 'created_at', 'updated_at')}),
    )


@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ['email', 'name', 'is_subscribed', 'source', 'created_at']
    list_editable = ['is_subscribed']
    list_display_links = ['email']
    search_fields = ['email', 'name']
    list_filter = ['is_subscribed', 'source', 'created_at']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at']
    actions = ['unsubscribe_selected', 'export_emails']

    @admin.action(description='Unsubscribe selected')
    def unsubscribe_selected(self, request, queryset):
        count = queryset.filter(is_subscribed=True).update(
            is_subscribed=False, unsubscribed_at=timezone.now()
        )
        self.message_user(request, f'{count} subscriber(s) unsubscribed.')

    @admin.action(description='Show emails of selected (for copy/paste)')
    def export_emails(self, request, queryset):
        emails = ', '.join(queryset.values_list('email', flat=True))
        self.message_user(request, emails or 'No subscribers selected.')
