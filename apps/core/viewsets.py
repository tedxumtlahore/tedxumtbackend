from rest_framework import viewsets
from rest_framework.response import Response

from .models import WebsiteSettings, HeroSection, NavigationItem, SocialLink, FAQ
from .serializers import (
    WebsiteSettingsSerializer,
    HeroSectionSerializer,
    NavigationItemSerializer,
    SocialLinkSerializer,
    FAQSerializer,
)


class SingletonViewSet(viewsets.ModelViewSet):
    serializer_class = None
    model = None

    http_method_names = ['get', 'put', 'patch', 'head', 'options']

    def get_queryset(self):
        return self.model.objects.all()

    def get_object(self):
        return self.model.load()

    def get_serializer_context(self):
        return {'request': self.request}

    def get_serializer(self, *args, **kwargs):
        kwargs.setdefault('context', self.get_serializer_context())
        return self.serializer_class(*args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_object())
        return Response(serializer.data)

    def list(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=False)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class WebsiteSettingsViewSet(SingletonViewSet):
    serializer_class = WebsiteSettingsSerializer
    model = WebsiteSettings


class HeroSectionViewSet(SingletonViewSet):
    serializer_class = HeroSectionSerializer
    model = HeroSection


class VisibleContentViewSet(viewsets.ReadOnlyModelViewSet):
    def get_queryset(self):
        return self.queryset.filter(is_visible=True)


class NavigationItemViewSet(VisibleContentViewSet):
    queryset = NavigationItem.objects.all()
    serializer_class = NavigationItemSerializer


class SocialLinkViewSet(VisibleContentViewSet):
    queryset = SocialLink.objects.all()
    serializer_class = SocialLinkSerializer


class FAQViewSet(VisibleContentViewSet):
    queryset = FAQ.objects.all()
    serializer_class = FAQSerializer
