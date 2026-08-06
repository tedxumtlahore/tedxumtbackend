from django.urls import include, path
from rest_framework.routers import SimpleRouter

from . import views
from .viewsets import (
    ContactMessageViewSet,
    NewsletterSubscriberViewSet,
    PartnerApplicationViewSet,
    SpeakerApplicationViewSet,
    VolunteerApplicationViewSet,
)

router = SimpleRouter()
router.register('contact-messages', ContactMessageViewSet, basename='contact-message')
router.register('newsletter-subscribers', NewsletterSubscriberViewSet, basename='newsletter-subscriber')
router.register('speaker-applications', SpeakerApplicationViewSet, basename='speaker-application')
router.register('volunteer-applications', VolunteerApplicationViewSet, basename='volunteer-application')
router.register('partner-applications', PartnerApplicationViewSet, basename='partner-application')

urlpatterns = [
    path('apply/options/', views.application_options_view, name='api-apply-options'),

    # Friendly aliases the frontend posts to.
    path('contact/', ContactMessageViewSet.as_view({'post': 'create'}), name='api-contact'),
    path('newsletter/', NewsletterSubscriberViewSet.as_view({'post': 'create'}), name='api-newsletter'),
    path(
        'newsletter/unsubscribe/',
        NewsletterSubscriberViewSet.as_view({'post': 'unsubscribe'}),
        name='api-newsletter-unsubscribe',
    ),
    path('apply/speaker/', SpeakerApplicationViewSet.as_view({'post': 'create'}), name='api-apply-speaker'),
    path('apply/volunteer/', VolunteerApplicationViewSet.as_view({'post': 'create'}), name='api-apply-volunteer'),
    path('apply/partner/', PartnerApplicationViewSet.as_view({'post': 'create'}), name='api-apply-partner'),
    path('', include(router.urls)),
]
