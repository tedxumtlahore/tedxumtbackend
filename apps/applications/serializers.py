"""
Applications serializers.

Every serializer here is public-write / staff-read: the internal triage fields
(`status`, `internal_notes`, `submitted_ip`) are never writable from the website.
"""

from django.utils import timezone
from rest_framework import serializers

from .models import (
    ContactMessage,
    NewsletterSubscriber,
    PartnerApplication,
    SpeakerApplication,
    VolunteerApplication,
)

TRIAGE_READ_ONLY = ['id', 'status', 'submitted_ip', 'created_at', 'updated_at', 'is_active']

MIN_MESSAGE_LENGTH = 20


def _clean_text(value):
    return (value or '').strip()


class SubmissionSerializerMixin:
    """Strip surrounding whitespace and stamp the submitter's IP on create."""

    def validate_email(self, value):
        return _clean_text(value).lower()

    def create(self, validated_data):
        request = self.context.get('request')
        if request is not None and 'submitted_ip' in [f.name for f in self.Meta.model._meta.fields]:
            validated_data['submitted_ip'] = get_client_ip(request)
        return super().create(validated_data)


def get_client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


class ContactMessageSerializer(SubmissionSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = [
            'id', 'name', 'email', 'subject', 'message', 'status', 'is_read',
            'submitted_ip', 'created_at', 'updated_at', 'is_active',
        ]
        read_only_fields = TRIAGE_READ_ONLY + ['is_read']

    def validate_name(self, value):
        cleaned = _clean_text(value)
        if len(cleaned) < 2:
            raise serializers.ValidationError('Please enter your full name.')
        return cleaned

    def validate_subject(self, value):
        cleaned = _clean_text(value)
        if len(cleaned) < 3:
            raise serializers.ValidationError('Please give your message a subject.')
        return cleaned

    def validate_message(self, value):
        cleaned = _clean_text(value)
        if len(cleaned) < MIN_MESSAGE_LENGTH:
            raise serializers.ValidationError(
                f'Please write at least {MIN_MESSAGE_LENGTH} characters so we can help properly.'
            )
        return cleaned


class NewsletterSubscriberSerializer(serializers.ModelSerializer):
    # `email` is unique on the model, but signing up twice must re-subscribe
    # rather than 400 — so the auto-generated UniqueValidator is dropped and
    # the collision is resolved in create() instead.
    email = serializers.EmailField(validators=[])

    class Meta:
        model = NewsletterSubscriber
        fields = ['id', 'email', 'name', 'is_subscribed', 'source', 'created_at', 'updated_at']
        read_only_fields = ['id', 'is_subscribed', 'created_at', 'updated_at']

    def validate_email(self, value):
        return _clean_text(value).lower()

    def create(self, validated_data):
        """Signing up twice re-subscribes instead of erroring with a 400."""
        email = validated_data.pop('email')
        subscriber, created = NewsletterSubscriber.objects.get_or_create(
            email=email, defaults=validated_data
        )
        if not created:
            subscriber.is_subscribed = True
            subscriber.unsubscribed_at = None
            if validated_data.get('name'):
                subscriber.name = validated_data['name']
            subscriber.save()
        return subscriber


class NewsletterUnsubscribeSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def save(self, **kwargs):
        email = self.validated_data['email'].strip().lower()
        updated = NewsletterSubscriber.objects.filter(email=email, is_subscribed=True).update(
            is_subscribed=False, unsubscribed_at=timezone.now()
        )
        return updated > 0


class SpeakerApplicationSerializer(SubmissionSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = SpeakerApplication
        fields = [
            'id', 'full_name', 'email', 'phone', 'organization', 'designation',
            'talk_title', 'talk_summary', 'previous_experience', 'linkedin', 'video_url',
            'status', 'submitted_ip', 'created_at', 'updated_at', 'is_active',
        ]
        read_only_fields = TRIAGE_READ_ONLY

    def validate_full_name(self, value):
        cleaned = _clean_text(value)
        if len(cleaned) < 2:
            raise serializers.ValidationError('Please enter your full name.')
        return cleaned

    def validate_talk_title(self, value):
        cleaned = _clean_text(value)
        if len(cleaned) < 3:
            raise serializers.ValidationError('Please give your talk a working title.')
        return cleaned

    def validate_talk_summary(self, value):
        cleaned = _clean_text(value)
        if len(cleaned) < 50:
            raise serializers.ValidationError(
                'Tell us more — at least 50 characters about the idea you want to share.'
            )
        return cleaned


class VolunteerApplicationSerializer(SubmissionSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = VolunteerApplication
        fields = [
            'id', 'full_name', 'email', 'phone', 'university', 'student_id',
            'preferred_department', 'availability', 'skills', 'motivation',
            'status', 'submitted_ip', 'created_at', 'updated_at', 'is_active',
        ]
        read_only_fields = TRIAGE_READ_ONLY

    def validate_full_name(self, value):
        cleaned = _clean_text(value)
        if len(cleaned) < 2:
            raise serializers.ValidationError('Please enter your full name.')
        return cleaned

    def validate_motivation(self, value):
        cleaned = _clean_text(value)
        if len(cleaned) < MIN_MESSAGE_LENGTH:
            raise serializers.ValidationError(
                f'Please write at least {MIN_MESSAGE_LENGTH} characters about why you want to join.'
            )
        return cleaned


class PartnerApplicationSerializer(SubmissionSerializerMixin, serializers.ModelSerializer):
    interested_tier_name = serializers.CharField(source='interested_tier.name', read_only=True)

    class Meta:
        model = PartnerApplication
        fields = [
            'id', 'organization_name', 'contact_person', 'email', 'phone', 'website',
            'partnership_type', 'interested_tier', 'interested_tier_name', 'proposal',
            'status', 'submitted_ip', 'created_at', 'updated_at', 'is_active',
        ]
        read_only_fields = TRIAGE_READ_ONLY

    def validate_organization_name(self, value):
        cleaned = _clean_text(value)
        if len(cleaned) < 2:
            raise serializers.ValidationError('Please enter your organization name.')
        return cleaned

    def validate_proposal(self, value):
        cleaned = _clean_text(value)
        if len(cleaned) < MIN_MESSAGE_LENGTH:
            raise serializers.ValidationError(
                f'Please describe the partnership in at least {MIN_MESSAGE_LENGTH} characters.'
            )
        return cleaned
