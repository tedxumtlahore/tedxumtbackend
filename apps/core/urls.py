from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views
from .viewsets import WebsiteSettingsViewSet, HeroSectionViewSet, NavigationItemViewSet, SocialLinkViewSet, FAQViewSet

router = DefaultRouter()
router.register('website-settings', WebsiteSettingsViewSet, basename='website-settings')
router.register('hero', HeroSectionViewSet, basename='hero')
router.register('navigation-items', NavigationItemViewSet, basename='navigation-item')
router.register('social-links', SocialLinkViewSet, basename='social-link')
router.register('faqs', FAQViewSet, basename='faq')

urlpatterns = [
    path('settings/', views.settings_view, name='api-settings'),
    path('navigation/', views.navigation_view, name='api-navigation'),
    path('', include(router.urls)),
]
