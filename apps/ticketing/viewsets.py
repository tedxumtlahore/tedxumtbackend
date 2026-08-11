"""
Staff-facing ticketing collections.

Read-only on purpose: registrations, orders, and tickets are created and
advanced by `services.py`, never by a PATCH from a client. Organizers change
state through the admin's audited actions.
"""

from rest_framework import viewsets

from apps.common.mixins import SerializerContextMixin
from apps.common.pagination import DefaultPagination
from apps.common.permissions import IsOrganizer

from .models import CheckInLog, Order, Registration, Ticket
from .serializers import (
    CheckInLogSerializer,
    OrderAdminSerializer,
    RegistrationAdminSerializer,
    TicketAdminSerializer,
)


class OrganizerReadOnlyViewSet(SerializerContextMixin, viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsOrganizer]
    pagination_class = DefaultPagination


class RegistrationViewSet(OrganizerReadOnlyViewSet):
    queryset = Registration.objects.select_related('event', 'order', 'ticket')
    serializer_class = RegistrationAdminSerializer
    lookup_field = 'public_ref'
    filterset_fields = ['status', 'event']
    search_fields = ['full_name', 'email', 'phone', 'university', 'occupation']
    ordering_fields = ['created_at', 'full_name', 'status']

    def get_queryset(self):
        queryset = super().get_queryset()
        event = self.request.query_params.get('event_slug')
        if event:
            queryset = queryset.filter(event__slug=event)
        return queryset


class OrderViewSet(OrganizerReadOnlyViewSet):
    queryset = Order.objects.select_related('registration', 'registration__event', 'confirmed_by')
    serializer_class = OrderAdminSerializer
    filterset_fields = ['status', 'provider']
    search_fields = ['reference', 'registration__full_name', 'registration__email']
    ordering_fields = ['created_at', 'paid_at', 'amount']


class TicketViewSet(OrganizerReadOnlyViewSet):
    queryset = Ticket.objects.select_related(
        'registration', 'registration__event', 'checked_in_by'
    )
    serializer_class = TicketAdminSerializer
    lookup_field = 'ticket_number'
    lookup_value_regex = '[^/]+'
    filterset_fields = ['checked_in']
    search_fields = ['ticket_number', 'registration__full_name', 'registration__email']
    ordering_fields = ['created_at', 'checked_in_at', 'ticket_number']

    def get_queryset(self):
        queryset = super().get_queryset()
        event = self.request.query_params.get('event_slug')
        if event:
            queryset = queryset.filter(registration__event__slug=event)
        return queryset


class CheckInLogViewSet(OrganizerReadOnlyViewSet):
    queryset = CheckInLog.objects.select_related(
        'ticket', 'ticket__registration', 'event', 'volunteer'
    )
    serializer_class = CheckInLogSerializer
    filterset_fields = ['result', 'event']
    ordering_fields = ['created_at']
