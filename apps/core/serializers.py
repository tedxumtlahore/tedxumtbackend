"""
Core serializers - WebsiteSettings, Hero, Navigation, SocialLinks, FAQ.
"""

from rest_framework import serializers

from apps.common.utils import get_file_url

from .models import WebsiteSettings, HeroSection, NavigationItem, SocialLink, FAQ


class WebsiteSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebsiteSettings
        fields = [
            'id',
            'site_name',
            'tagline',
            'description',
            'events_count',
            'speakers_count',
            'attendees_count',
            'about_summary',
            'email',
            'phone',
            'address',
            'map_embed_url',
            'copyright_text',
            'footer_tagline',
            'ted_event_url',
            'created_at',
            'updated_at',
            'is_active',
        ]


class HeroSectionSerializer(serializers.ModelSerializer):
    background_image = serializers.SerializerMethodField()

    class Meta:
        model = HeroSection
        fields = [
            'id',
            'eyebrow',
            'headline_line1',
            'headline_line2',
            'subheading',
            'cta_primary_label',
            'cta_primary_url',
            'cta_secondary_label',
            'cta_secondary_url',
            'background_image',
            'created_at',
            'updated_at',
            'is_active',
        ]

    def get_background_image(self, obj):
        request = self.context.get('request')
        return get_file_url(request, obj.background_image)


class NavigationItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = NavigationItem
        fields = [
            'id',
            'label',
            'url',
            'order',
            'is_visible',
            'open_in_new_tab',
            'created_at',
            'updated_at',
            'is_active',
        ]


class SocialLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = SocialLink
        fields = [
            'id',
            'platform',
            'url',
            'display_label',
            'aria_label',
            'order',
            'is_visible',
            'created_at',
            'updated_at',
            'is_active',
        ]


class FAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQ
        fields = [
            'id',
            'question',
            'answer',
            'order',
            'is_visible',
            'created_at',
            'updated_at',
            'is_active',
        ]
