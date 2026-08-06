from django.urls import include, path
from rest_framework.routers import SimpleRouter

from . import views
from .viewsets import BlogPostViewSet, CategoryViewSet, TagViewSet

router = SimpleRouter()
router.register('blog-categories', CategoryViewSet, basename='blog-category')
router.register('blog-tags', TagViewSet, basename='blog-tag')
router.register('blog-posts', BlogPostViewSet, basename='blog-post')

urlpatterns = [
    path('blog/', views.blog_index_view, name='api-blog'),
    path('', include(router.urls)),
]
