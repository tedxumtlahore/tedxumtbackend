"""
Core views — flat read-only endpoints for global site content.

`site_config_view` is the one the SPA calls on boot; the rest are single-purpose
aliases kept because they read better in the browsable API.
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import FAQ, HeroSection, NavigationItem, SocialLink, WebsiteSettings
from .serializers import (
    FAQSerializer,
    HeroSectionSerializer,
    NavigationItemSerializer,
    SocialLinkSerializer,
    WebsiteSettingsSerializer,
)


def _visible_navigation():
    return NavigationItem.objects.filter(is_active=True, is_visible=True).order_by('order', 'label')


def _visible_social_links():
    return SocialLink.objects.filter(is_active=True, is_visible=True).order_by('order', 'platform')


def _visible_faqs():
    return FAQ.objects.filter(is_active=True, is_visible=True).order_by('order', 'question')


@api_view(['GET'])
@permission_classes([AllowAny])
def settings_view(request):
    """GET /api/settings/ — global site settings."""
    serializer = WebsiteSettingsSerializer(WebsiteSettings.load(), context={'request': request})
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def hero_view(request):
    """GET /api/hero/ — homepage hero content."""
    serializer = HeroSectionSerializer(HeroSection.load(), context={'request': request})
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def navigation_view(request):
    """GET /api/navigation/ — ordered, visible nav items."""
    serializer = NavigationItemSerializer(_visible_navigation(), many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def social_links_view(request):
    """GET /api/social/ — visible social links."""
    serializer = SocialLinkSerializer(_visible_social_links(), many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def faq_view(request):
    """GET /api/faq/ — visible FAQs in order."""
    serializer = FAQSerializer(_visible_faqs(), many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def site_config_view(request):
    """
    GET /api/site-config/ — everything the shell needs in one request.

    The SPA calls this once on boot instead of firing four separate requests
    for settings, hero, navigation, and social links.
    """
    context = {'request': request}
    return Response({
        'settings': WebsiteSettingsSerializer(WebsiteSettings.load(), context=context).data,
        'hero': HeroSectionSerializer(HeroSection.load(), context=context).data,
        'navigation': NavigationItemSerializer(_visible_navigation(), many=True, context=context).data,
        'social_links': SocialLinkSerializer(_visible_social_links(), many=True, context=context).data,
        'faqs': FAQSerializer(_visible_faqs(), many=True, context=context).data,
    })
