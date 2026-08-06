from django.db.models import Prefetch
from rest_framework import viewsets

from apps.common.mixins import SerializerContextMixin, VisibleQuerysetMixin
from apps.common.pagination import DefaultPagination
from apps.common.permissions import IsStaffOrReadOnly

from .models import Department, TeamMember
from .serializers import DepartmentDetailSerializer, DepartmentSerializer, TeamMemberSerializer


class DepartmentViewSet(SerializerContextMixin, VisibleQuerysetMixin, viewsets.ModelViewSet):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    permission_classes = [IsStaffOrReadOnly]
    pagination_class = DefaultPagination
    lookup_field = 'slug'
    search_fields = ['name', 'description']
    ordering_fields = ['order', 'name', 'created_at']

    def get_queryset(self):
        members = TeamMember.objects.select_related('department')
        return super().get_queryset().prefetch_related(Prefetch('members', queryset=members))

    def get_serializer_class(self):
        if self.action in {'list', 'retrieve'}:
            return DepartmentDetailSerializer
        return DepartmentSerializer


class TeamMemberViewSet(SerializerContextMixin, VisibleQuerysetMixin, viewsets.ModelViewSet):
    queryset = TeamMember.objects.select_related('department')
    serializer_class = TeamMemberSerializer
    permission_classes = [IsStaffOrReadOnly]
    pagination_class = DefaultPagination
    lookup_field = 'slug'
    filterset_fields = ['department__slug']
    search_fields = ['name', 'role', 'bio', 'department__name']
    ordering_fields = ['order', 'name', 'created_at']

    def get_queryset(self):
        queryset = super().get_queryset()
        department = self.request.query_params.get('department')
        if department:
            queryset = queryset.filter(department__slug=department)
        return queryset
