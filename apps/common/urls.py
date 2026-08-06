from django.urls import path

from . import views

urlpatterns = [
    path('common/health/', views.health_view, name='common-health'),
    path('common/status-choices/', views.status_choices_view, name='common-status-choices'),
]
