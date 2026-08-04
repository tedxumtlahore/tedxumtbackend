"""
Core serializers — WebsiteSettings, Hero, Navigation, SocialLinks, FAQ.
"""

from rest_framework import serializers
from .models import WebsiteSettings, HeroSection, NavigationItem, SocialLink, FAQ


class WebsiteSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebsiteSettings
        exclude = ['id']


class HeroSectionSerializer(serializers.ModelSerializer):
    background_image = serializers.SerializerMethodField()

    class Meta:
        model = HeroSection
        exclude = ['id']

    def get_background_image(self, obj):
        if obj.background_image:
            request = self.context.get('request')
            return request.build_absolute_uri(obj.background_image.url) if request else obj.background_image.url
        return None


class NavigationItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = NavigationItem
        fields = ['id', 'label', 'url', 'order', 'open_in_new_tab']


class SocialLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = SocialLink
        fields = ['id', 'platform', 'url', 'display_label', 'aria_label', 'order']


class FAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQ
        fields = ['id', 'question', 'answer', 'order']
