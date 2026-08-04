"""
Core views — read-only API endpoints for global settings.
"""

from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import WebsiteSettings, HeroSection, NavigationItem, SocialLink, FAQ
from .serializers import (
    WebsiteSettingsSerializer,
    HeroSectionSerializer,
    NavigationItemSerializer,
    SocialLinkSerializer,
    FAQSerializer,
)


@api_view(['GET'])
def settings_view(request):
    """GET /api/settings/ — global site settings."""
    obj = WebsiteSettings.load()
    serializer = WebsiteSettingsSerializer(obj, context={'request': request})
    return Response(serializer.data)


@api_view(['GET'])
def hero_view(request):
    """GET /api/hero/ — active hero section content."""
    obj = HeroSection.load()
    serializer = HeroSectionSerializer(obj, context={'request': request})
    return Response(serializer.data)


@api_view(['GET'])
def navigation_view(request):
    """GET /api/navigation/ — ordered, visible nav items."""
    items = NavigationItem.objects.filter(is_visible=True)
    serializer = NavigationItemSerializer(items, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def social_links_view(request):
    """GET /api/social-links/ — visible social links."""
    links = SocialLink.objects.filter(is_visible=True)
    serializer = SocialLinkSerializer(links, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def faq_view(request):
    """GET /api/faqs/ — visible FAQs in order."""
    faqs = FAQ.objects.filter(is_visible=True)
    serializer = FAQSerializer(faqs, many=True)
    return Response(serializer.data)
