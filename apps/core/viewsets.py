from rest_framework import viewsets
from rest_framework.response import Response

from apps.common.mixins import SerializerContextMixin, VisibleQuerysetMixin
from apps.common.permissions import IsStaffOrReadOnly

from .models import FAQ, HeroSection, NavigationItem, SocialLink, WebsiteSettings
from .serializers import (
    FAQSerializer,
    HeroSectionSerializer,
    NavigationItemSerializer,
    SocialLinkSerializer,
    WebsiteSettingsSerializer,
)


class SingletonViewSet(SerializerContextMixin, viewsets.ModelViewSet):
    """
    Exposes a one-row model at a single URL.

    Both /<resource>/ and /<resource>/1/ return the same object, so the
    frontend never has to know the row exists before reading it.
    """

    serializer_class = None
    model = None
    permission_classes = [IsStaffOrReadOnly]
    pagination_class = None

    http_method_names = ['get', 'put', 'patch', 'head', 'options']

    def get_queryset(self):
        return self.model.objects.all()

    def get_object(self):
        return self.model.load()

    def retrieve(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_object())
        return Response(serializer.data)

    def list(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=kwargs.pop('partial', False))
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)


class WebsiteSettingsViewSet(SingletonViewSet):
    serializer_class = WebsiteSettingsSerializer
    model = WebsiteSettings


class HeroSectionViewSet(SingletonViewSet):
    serializer_class = HeroSectionSerializer
    model = HeroSection


class VisibleContentViewSet(SerializerContextMixin, VisibleQuerysetMixin, viewsets.ModelViewSet):
    permission_classes = [IsStaffOrReadOnly]
    pagination_class = None  # these lists are short and always rendered whole


class NavigationItemViewSet(VisibleContentViewSet):
    queryset = NavigationItem.objects.all()
    serializer_class = NavigationItemSerializer
    search_fields = ['label', 'url']
    ordering_fields = ['order', 'label']


class SocialLinkViewSet(VisibleContentViewSet):
    queryset = SocialLink.objects.all()
    serializer_class = SocialLinkSerializer
    filterset_fields = ['platform']
    search_fields = ['display_label', 'url', 'aria_label']
    ordering_fields = ['order', 'platform']


class FAQViewSet(VisibleContentViewSet):
    queryset = FAQ.objects.all()
    serializer_class = FAQSerializer
    search_fields = ['question', 'answer']
    ordering_fields = ['order', 'question']
