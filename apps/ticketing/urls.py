from django.urls import include, path
from rest_framework.routers import SimpleRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView

from . import views
from .viewsets import CheckInLogViewSet, OrderViewSet, RegistrationViewSet, TicketViewSet

router = SimpleRouter()
router.register('registrations', RegistrationViewSet, basename='registration')
router.register('orders', OrderViewSet, basename='order')
router.register('tickets', TicketViewSet, basename='ticket')
router.register('check-in-logs', CheckInLogViewSet, basename='check-in-log')

urlpatterns = [
    # Auth for the volunteer scanner. The CMS keeps using session auth; JWT
    # exists so a phone app can hold a credential without the CSRF dance.
    path('auth/token/', TokenObtainPairView.as_view(), name='token-obtain'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('auth/token/verify/', TokenVerifyView.as_view(), name='token-verify'),

    # Attendee
    path('events/<slug:slug>/ticketing/', views.event_ticketing_view, name='api-event-ticketing'),
    path('events/<slug:slug>/register/', views.register_view, name='api-event-register'),
    path(
        'registrations/status/<uuid:public_ref>/',
        views.registration_status_view,
        name='api-registration-status',
    ),
    path(
        'tickets/by-token/<uuid:access_token>/',
        views.ticket_by_token_view,
        name='api-ticket-by-token',
    ),

    # Volunteer check-in
    path('checkin/verify/', views.check_in_verify_view, name='api-checkin-verify'),
    path('checkin/', views.check_in_view, name='api-checkin'),
    path('checkin/history/', views.check_in_history_view, name='api-checkin-history'),

    path('', include(router.urls)),
]
