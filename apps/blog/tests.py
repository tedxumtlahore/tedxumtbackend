from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase

from apps.common.models import StatusChoices

from .models import BlogPost, Category, Tag


class BlogModelTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Reflections')

    def test_publishing_stamps_published_at(self):
        post = BlogPost.objects.create(
            title='Why Ideas Need Rooms',
            excerpt='Short',
            content='word ' * 400,
            category=self.category,
        )
        self.assertIsNone(post.published_at)

        post.status = StatusChoices.PUBLISHED
        post.save()

        self.assertIsNotNone(post.published_at)

    def test_publish_date_is_not_overwritten_on_later_saves(self):
        post = BlogPost.objects.create(
            title='Curating Resonance', excerpt='Short', content='Body',
            category=self.category, status=StatusChoices.PUBLISHED,
        )
        original = post.published_at

        post.title = 'Curating Resonance, Revisited'
        post.save()

        self.assertEqual(post.published_at, original)

    def test_reading_minutes_estimated_from_content(self):
        post = BlogPost.objects.create(
            title='Long Read', excerpt='Short', content='word ' * 600, category=self.category,
        )
        self.assertEqual(post.reading_minutes, 3)

    def test_explicit_reading_minutes_is_respected(self):
        post = BlogPost.objects.create(
            title='Manual Estimate', excerpt='Short', content='word ' * 600,
            category=self.category, reading_minutes=9,
        )
        self.assertEqual(post.reading_minutes, 9)


class BlogAPITests(APITestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Reflections')
        self.tag = Tag.objects.create(name='Behind the Scenes')
        self.featured = BlogPost.objects.create(
            title='Featured Post', excerpt='Lead', content='Body',
            category=self.category, status=StatusChoices.PUBLISHED, is_featured=True,
        )
        self.featured.tags.add(self.tag)
        self.published = BlogPost.objects.create(
            title='Second Post', excerpt='More', content='Body',
            category=self.category, status=StatusChoices.PUBLISHED,
        )
        self.draft = BlogPost.objects.create(
            title='Secret Draft', excerpt='Hidden', content='Body', category=self.category,
        )

    def test_blog_index_splits_featured_from_the_rest(self):
        response = self.client.get(reverse('api-blog'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['featured']['title'], 'Featured Post')
        self.assertEqual([p['title'] for p in response.data['posts']], ['Second Post'])

    def test_drafts_are_hidden_from_anonymous_users(self):
        response = self.client.get('/api/blog-posts/')

        titles = [p['title'] for p in response.data['results']]
        self.assertNotIn('Secret Draft', titles)
        self.assertEqual(len(titles), 2)

    def test_staff_can_preview_drafts(self):
        get_user_model().objects.create_superuser('editor', 'e@example.com', 'pw-strong-123')
        self.client.login(username='editor', password='pw-strong-123')

        response = self.client.get('/api/blog-posts/')

        self.assertIn('Secret Draft', [p['title'] for p in response.data['results']])

    def test_draft_detail_is_404_for_anonymous_users(self):
        response = self.client.get(f'/api/blog-posts/{self.draft.slug}/')

        self.assertEqual(response.status_code, 404)

    def test_detail_includes_content_and_related_posts(self):
        response = self.client.get(f'/api/blog-posts/{self.featured.slug}/')

        self.assertEqual(response.status_code, 200)
        self.assertIn('content', response.data)
        self.assertEqual([p['title'] for p in response.data['related_posts']], ['Second Post'])

    def test_filter_posts_by_tag(self):
        response = self.client.get('/api/blog-posts/', {'tag': self.tag.slug})

        self.assertEqual([p['title'] for p in response.data['results']], ['Featured Post'])

    def test_category_post_count_only_counts_published(self):
        response = self.client.get('/api/blog-categories/')

        self.assertEqual(response.data['results'][0]['post_count'], 2)

    def test_anonymous_users_cannot_create_posts(self):
        response = self.client.post('/api/blog-posts/', {
            'title': 'Spam', 'excerpt': 'x', 'content': 'x', 'category': self.category.pk,
        })

        self.assertEqual(response.status_code, 403)
