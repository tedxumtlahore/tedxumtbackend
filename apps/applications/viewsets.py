"""
Applications viewsets.

Anonymous visitors may only POST. Reading, editing, and triaging submissions
is staff-only — these payloads contain personal data.
"""

from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common.pagination import DefaultPagination
from apps.common.permissions import CreateOnlyOrStaff

from .models import (
    ContactMessage,
    NewsletterSubscriber,
    PartnerApplication,
    SpeakerApplication,
    VolunteerApplication,
)
from .serializers import (
    ContactMessageSerializer,
    NewsletterSubscriberSerializer,
    NewsletterUnsubscribeSerializer,
    PartnerApplicationSerializer,
    SpeakerApplicationSerializer,
    VolunteerApplicationSerializer,
)
from .throttling import NewsletterRateThrottle, SubmissionRateThrottle


class SubmissionViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Public create, staff-only everything else."""

    permission_classes = [CreateOnlyOrStaff]
    pagination_class = DefaultPagination
    throttle_classes = [SubmissionRateThrottle]
    ordering_fields = ['created_at', 'status']

    def get_throttles(self):
        # Staff triaging the inbox should never hit the public submission limit.
        user = getattr(self.request, 'user', None)
        if user is not None and user.is_staff:
            return []
        return super().get_throttles()

    def get_queryset(self):
        queryset = super().get_queryset()
        submission_status = self.request.query_params.get('status')
        if submission_status:
            queryset = queryset.filter(status=submission_status)
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {
                'success': True,
                'message': self.success_message,
                'id': serializer.data.get('id'),
            },
            status=status.HTTP_201_CREATED,
        )

    success_message = 'Submission received.'


class ContactMessageViewSet(SubmissionViewSet):
    queryset = ContactMessage.objects.all()
    serializer_class = ContactMessageSerializer
    search_fields = ['name', 'email', 'subject', 'message']
    success_message = "Message sent — we'll be in touch soon."

    @action(detail=True, methods=['post'], url_path='mark-read')
    def mark_read(self, request, pk=None):
        message = self.get_object()
        message.is_read = True
        message.save(update_fields=['is_read', 'updated_at'])
        return Response({'success': True, 'is_read': True})


class SpeakerApplicationViewSet(SubmissionViewSet):
    queryset = SpeakerApplication.objects.all()
    serializer_class = SpeakerApplicationSerializer
    search_fields = ['full_name', 'email', 'talk_title', 'talk_summary', 'organization']
    success_message = 'Application received — our programming team reviews these on a rolling basis.'


class VolunteerApplicationViewSet(SubmissionViewSet):
    queryset = VolunteerApplication.objects.all()
    serializer_class = VolunteerApplicationSerializer
    search_fields = ['full_name', 'email', 'university', 'preferred_department', 'skills']
    success_message = "Application received — we'll reach out when the next intake opens."


class PartnerApplicationViewSet(SubmissionViewSet):
    queryset = PartnerApplication.objects.select_related('interested_tier')
    serializer_class = PartnerApplicationSerializer
    search_fields = ['organization_name', 'contact_person', 'email', 'proposal']
    success_message = 'Thanks — our partnerships team will get back to you shortly.'


class NewsletterSubscriberViewSet(SubmissionViewSet):
    queryset = NewsletterSubscriber.objects.all()
    serializer_class = NewsletterSubscriberSerializer
    throttle_classes = [NewsletterRateThrottle]
    search_fields = ['email', 'name']
    success_message = 'Subscribed — welcome to the list.'

    def get_queryset(self):
        # NewsletterSubscriber has no `status` field, so skip the base filter.
        queryset = NewsletterSubscriber.objects.all()
        subscribed = self.request.query_params.get('subscribed')
        if subscribed in {'1', 'true', 'True'}:
            queryset = queryset.filter(is_subscribed=True)
        elif subscribed in {'0', 'false', 'False'}:
            queryset = queryset.filter(is_subscribed=False)
        return queryset

    @action(detail=False, methods=['post'], permission_classes=[])
    def unsubscribe(self, request):
        serializer = NewsletterUnsubscribeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        removed = serializer.save()
        return Response({
            'success': True,
            'message': 'You have been unsubscribed.' if removed else 'That address was not subscribed.',
        })
