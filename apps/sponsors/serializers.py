"""Sponsors serializers - tiers with nested sponsors."""

from rest_framework import serializers

from apps.common.utils import get_file_url

from .models import Sponsor, SponsorTier


class SponsorSerializer(serializers.ModelSerializer):
    logo = serializers.SerializerMethodField()
    logo_upload = serializers.ImageField(source='logo', write_only=True, required=False)
    tier_name = serializers.CharField(source='tier.name', read_only=True)
    tier_slug = serializers.CharField(source='tier.slug', read_only=True)
    event_title = serializers.CharField(source='event.title', read_only=True)

    class Meta:
        model = Sponsor
        fields = [
            'id', 'name', 'slug', 'tier', 'tier_name', 'tier_slug', 'logo', 'logo_upload',
            'website', 'description', 'event', 'event_title', 'order', 'is_visible',
            'created_at', 'updated_at', 'is_active',
        ]
        read_only_fields = ['id', 'slug', 'created_at', 'updated_at']

    def get_logo(self, obj):
        return get_file_url(self.context.get('request'), obj.logo)


class SponsorTierSerializer(serializers.ModelSerializer):
    benefit_list = serializers.SerializerMethodField()

    class Meta:
        model = SponsorTier
        fields = [
            'id', 'name', 'slug', 'description', 'benefits', 'benefit_list', 'order',
            'is_visible', 'created_at', 'updated_at', 'is_active',
        ]
        read_only_fields = ['id', 'slug', 'created_at', 'updated_at']

    def get_benefit_list(self, obj):
        return obj.benefit_list


class SponsorTierDetailSerializer(SponsorTierSerializer):
    sponsors = serializers.SerializerMethodField()

    class Meta(SponsorTierSerializer.Meta):
        fields = SponsorTierSerializer.Meta.fields + ['sponsors']

    def get_sponsors(self, obj):
        if not obj.pk:
            return []
        sponsors = [s for s in obj.sponsors.all() if s.is_visible and s.is_active]
        return SponsorSerializer(sponsors, many=True, context=self.context).data
