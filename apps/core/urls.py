from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views
from .viewsets import NavigationItemViewSet, SocialLinkViewSet, FAQViewSet

router = DefaultRouter()
router.register('navigation-items', NavigationItemViewSet, basename='navigation-item')
router.register('social-links', SocialLinkViewSet, basename='social-link')
router.register('faqs', FAQViewSet, basename='faq')

urlpatterns = [
    path('settings/', views.settings_view, name='api-settings'),
    path('hero/', views.hero_view, name='api-hero'),
    path('navigation/', views.navigation_view, name='api-navigation'),
    path('social-links/', views.social_links_view, name='api-social-links'),
    path('faqs/', views.faq_view, name='api-faqs'),
    path('', include(router.urls)),
]
