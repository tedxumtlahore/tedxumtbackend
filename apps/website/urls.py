from django.urls import include, path
from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register('about-sections', views.AboutSectionViewSet, basename='about-section')
router.register('core-values', views.CoreValueViewSet, basename='core-value')
router.register('messages', views.MessageViewSet, basename='message')

urlpatterns = [
    path('about/', views.about_view, name='api-about'),
    path('founder/', views.founder_view, name='api-founder'),
    path('', include(router.urls)),
]
