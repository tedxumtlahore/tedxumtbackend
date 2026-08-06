from django.urls import include, path
from rest_framework.routers import SimpleRouter

from . import views
from .viewsets import (
    FAQViewSet,
    HeroSectionViewSet,
    NavigationItemViewSet,
    SocialLinkViewSet,
    WebsiteSettingsViewSet,
)

router = SimpleRouter()
router.register('navigation-items', NavigationItemViewSet, basename='navigation-item')
router.register('social-links', SocialLinkViewSet, basename='social-link')
router.register('faqs', FAQViewSet, basename='faq')

# The singleton resources are one row at one URL, so they get explicit paths.
# A router would only map GET/POST onto the collection URL and push the writes
# down to /<pk>/, which is misleading for a model that only ever has one row.
SINGLETON_ACTIONS = {'get': 'retrieve', 'put': 'update', 'patch': 'partial_update'}

urlpatterns = [
    # Flat, single-purpose aliases used by the website.
    path('settings/', views.settings_view, name='api-settings'),
    path('site-config/', views.site_config_view, name='api-site-config'),
    path('navigation/', views.navigation_view, name='api-navigation'),
    path('social/', views.social_links_view, name='api-social-links'),
    path('faq/', views.faq_view, name='api-faq'),

    # Editable singletons.
    path(
        'website-settings/',
        WebsiteSettingsViewSet.as_view(SINGLETON_ACTIONS),
        name='website-settings',
    ),
    path('hero/', HeroSectionViewSet.as_view(SINGLETON_ACTIONS), name='hero'),

    path('', include(router.urls)),
]
