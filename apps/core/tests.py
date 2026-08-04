from django.test import SimpleTestCase

from .models import SocialLink, NavigationItem, FAQ
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
