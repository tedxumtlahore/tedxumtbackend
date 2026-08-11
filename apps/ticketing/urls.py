from django.urls import include, path
from rest_framework.routers import SimpleRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView

from . import dashboard, views
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
    path('payment-accounts/', views.payment_accounts_view, name='api-payment-accounts'),
    path(
        'registrations/status/<uuid:public_ref>/',
        views.registration_status_view,
        name='api-registration-status',
    ),
    path(
        'registrations/status/<uuid:public_ref>/payment-proof/',
        views.payment_proof_view,
        name='api-payment-proof',
    ),
    path(
        'tickets/by-token/<uuid:access_token>/',
        views.ticket_by_token_view,
        name='api-ticket-by-token',
    ),
    path(
        'tickets/by-token/<uuid:access_token>/qr.png',
        views.ticket_qr_view,
        name='api-ticket-qr',
    ),
    path(
        'tickets/by-token/<uuid:access_token>/pdf/',
        views.ticket_pdf_view,
        name='api-ticket-pdf',
    ),
    path(
        'tickets/<str:ticket_number>/resend/',
        views.resend_ticket_view,
        name='api-ticket-resend',
    ),

    # Organizer dashboard. Registered before the router so /registrations/export/
    # is not swallowed by the registration detail route.
    path('dashboard/', dashboard.dashboard_view, name='api-dashboard'),
    path('analytics/', dashboard.analytics_view, name='api-analytics'),
    path(
        'registrations/export/',
        dashboard.export_registrations_view,
        name='api-registrations-export',
    ),

    # Volunteer check-in
    path('checkin/verify/', views.check_in_verify_view, name='api-checkin-verify'),
    path('checkin/', views.check_in_view, name='api-checkin'),
    path('checkin/history/', views.check_in_history_view, name='api-checkin-history'),

    path('', include(router.urls)),
]
