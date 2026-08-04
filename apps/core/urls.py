from django.urls import path
from . import views

urlpatterns = [
    path('settings/', views.settings_view, name='api-settings'),
    path('hero/', views.hero_view, name='api-hero'),
    path('navigation/', views.navigation_view, name='api-navigation'),
    path('social-links/', views.social_links_view, name='api-social-links'),
    path('faqs/', views.faq_view, name='api-faqs'),
]
