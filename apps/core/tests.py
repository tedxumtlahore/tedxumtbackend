from django.test import SimpleTestCase
from django.urls import reverse
from rest_framework.test import APITestCase

from apps.common.testing import login_as_staff

from .models import SocialLink, NavigationItem, FAQ, WebsiteSettings
from .serializers import SocialLinkSerializer, NavigationItemSerializer, FAQSerializer


class CoreModelAndSerializerTests(SimpleTestCase):
    def test_social_link_platform_choices_use_textchoices(self):
        self.assertEqual(SocialLink.PlatformChoices.INSTAGRAM, 'instagram')
        self.assertEqual(SocialLink.PlatformChoices.LINKEDIN, 'linkedin')

    def test_navigation_item_serializer_exposes_expected_fields(self):
        item = NavigationItem(label='Home', url='/', order=1, is_visible=True, open_in_new_tab=False)
        serializer = NavigationItemSerializer(item)

        self.assertEqual(serializer.data['label'], 'Home')
        self.assertIn('created_at', serializer.data)
        self.assertIn('is_active', serializer.data)

    def test_social_link_serializer_exposes_visibility(self):
        link = SocialLink(
            platform=SocialLink.PlatformChoices.INSTAGRAM,
            url='https://instagram.com/tedxumt',
            display_label='IG',
            aria_label='Instagram',
            order=1,
            is_visible=True,
        )
        serializer = SocialLinkSerializer(link)

        self.assertEqual(serializer.data['platform'], 'instagram')
        self.assertTrue(serializer.data['is_visible'])

    def test_faq_serializer_exposes_content(self):
        faq = FAQ(question='When is the event?', answer='Soon.', order=1, is_visible=True)
        serializer = FAQSerializer(faq)

        self.assertEqual(serializer.data['question'], 'When is the event?')
        self.assertEqual(serializer.data['answer'], 'Soon.')


class CoreAPITests(APITestCase):
    def setUp(self):
        NavigationItem.objects.create(label='Home', url='/', order=1)
        NavigationItem.objects.create(label='Hidden', url='/hidden', order=2, is_visible=False)
        SocialLink.objects.create(
            platform=SocialLink.PlatformChoices.INSTAGRAM,
            url='https://instagram.com/tedxumtlahore', display_label='IG', order=1,
        )
        FAQ.objects.create(question='Where is it held?', answer='UMT Auditorium.', order=1)

    def test_site_config_returns_the_whole_shell_payload(self):
        response = self.client.get(reverse('api-site-config'))

        self.assertEqual(response.status_code, 200)
        for key in ('settings', 'hero', 'navigation', 'social_links', 'faqs'):
            self.assertIn(key, response.data)

    def test_settings_singleton_is_created_on_first_read(self):
        self.assertEqual(WebsiteSettings.objects.count(), 0)

        response = self.client.get(reverse('api-settings'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(WebsiteSettings.objects.count(), 1)
        self.assertEqual(response.data['site_name'], 'TEDxUMT Lahore')

    def test_settings_singleton_never_creates_a_second_row(self):
        self.client.get(reverse('api-settings'))
        self.client.get(reverse('api-settings'))

        self.assertEqual(WebsiteSettings.objects.count(), 1)

    def test_hero_is_reachable_through_the_router(self):
        response = self.client.get('/api/hero/')

        self.assertEqual(response.status_code, 200)
        self.assertIn('headline_line1', response.data)

    def test_hidden_navigation_items_are_excluded(self):
        response = self.client.get(reverse('api-navigation'))

        self.assertEqual([item['label'] for item in response.data], ['Home'])

    def test_social_and_faq_aliases_resolve(self):
        self.assertEqual(self.client.get(reverse('api-social-links')).status_code, 200)
        self.assertEqual(self.client.get(reverse('api-faq')).status_code, 200)

    def test_anonymous_users_cannot_edit_site_settings(self):
        response = self.client.patch('/api/website-settings/', {'site_name': 'Hacked'}, format='json')

        self.assertEqual(response.status_code, 403)
        self.assertFalse(WebsiteSettings.objects.filter(site_name='Hacked').exists())

    def test_anonymous_users_cannot_edit_the_hero(self):
        response = self.client.patch('/api/hero/', {'headline_line1': 'Hacked'}, format='json')

        self.assertEqual(response.status_code, 403)

    def test_staff_can_edit_site_settings(self):
        login_as_staff(self.client, 'cms')

        response = self.client.patch(
            '/api/website-settings/', {'tagline': 'Ideas Worth Spreading, Lahore'}, format='json'
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(WebsiteSettings.load().tagline, 'Ideas Worth Spreading, Lahore')

    def test_api_root_lists_endpoint_groups(self):
        response = self.client.get('/api/')

        self.assertEqual(response.status_code, 200)
        self.assertIn('endpoints', response.data)
        self.assertIn('collections', response.data['endpoints'])

    def test_health_endpoint_reports_database_status(self):
        response = self.client.get('/api/health/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'ok')
        self.assertTrue(response.data['database'])
