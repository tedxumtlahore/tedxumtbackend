from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register('about-sections', views.AboutSectionViewSet, basename='about-section')
router.register('core-values', views.CoreValueViewSet, basename='core-value')
router.register('messages', views.MessageViewSet, basename='message')

urlpatterns = [
    path('about/', views.about_view, name='api-about'),
    path('', include(router.urls)),
]
