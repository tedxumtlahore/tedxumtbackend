from django.urls import include, path
from rest_framework.routers import SimpleRouter

from . import views
from .viewsets import DepartmentViewSet, TeamMemberViewSet

router = SimpleRouter()
router.register('departments', DepartmentViewSet, basename='department')
router.register('team-members', TeamMemberViewSet, basename='team-member')

urlpatterns = [
    path('team/', views.team_view, name='api-team'),
    path('', include(router.urls)),
]
