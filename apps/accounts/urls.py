from django.urls import path

from . import views

urlpatterns = [
    path('accounts/register/', views.register_account_view, name='account-register'),
    path('accounts/me/', views.me_view, name='account-me'),
    path('accounts/me/registrations/', views.my_registrations_view, name='account-registrations'),
    path(
        'accounts/me/registrations/claim/',
        views.claim_registration_view,
        name='account-claim-registration',
    ),
]
