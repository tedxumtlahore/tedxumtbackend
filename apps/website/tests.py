from django.db.utils import IntegrityError
from django.test import SimpleTestCase, TestCase

from .models import AboutSection, CoreValue, Message
from .serializers import AboutSectionSerializer, CoreValueSerializer, MessageSerializer


class WebsiteModelTests(SimpleTestCase):
    def test_about_section_uses_text_choices(self):
        self.assertEqual(AboutSection.SectionKeyChoices.OUR_STORY, 'our_story')
        self.assertEqual(AboutSection.ImagePositionChoices.RIGHT, 'right')

    def test_core_value_uses_text_choices(self):
        self.assertEqual(CoreValue.IconChoices.INNOVATION, 'innovation')
        self.assertEqual(CoreValue.IconChoices.IMPACT, 'impact')

    def test_message_uses_text_choices(self):
        self.assertEqual(Message.MessageTypeChoices.PRESIDENT, 'president')


class WebsiteSerializerTests(SimpleTestCase):
    def test_about_section_serializer_includes_system_fields(self):
        section = AboutSection(
            section_key=AboutSection.SectionKeyChoices.OUR_STORY,
            eyebrow='Story',
            heading='About TEDxUMT Lahore',
            body='Body',
            image_position=AboutSection.ImagePositionChoices.RIGHT,
            order=1,
            is_visible=True,
        )

        serializer = AboutSectionSerializer(section)

        self.assertEqual(serializer.data['section_key'], 'our_story')
        self.assertIn('created_at', serializer.data)
        self.assertIn('is_active', serializer.data)

    def test_core_value_serializer_exposes_title(self):
        value = CoreValue(
            icon_key=CoreValue.IconChoices.INNOVATION,
            title='Innovation',
            description='Desc',
            order=1,
        )

        serializer = CoreValueSerializer(value)
        self.assertEqual(serializer.data['title'], 'Innovation')

    def test_message_serializer_exposes_visibility(self):
        message = Message(
            message_type=Message.MessageTypeChoices.PRESIDENT,
            person_name='Ayesha Bint e Hamid',
            role_title='President',
            message_body='Welcome',
            order=1,
            is_visible=True,
        )

        serializer = MessageSerializer(message)
        self.assertTrue(serializer.data['is_visible'])


class FounderTests(TestCase):
    """
    The Founder page is a `Message` with `message_type='founder'`, served by the
    existing MessageViewSet through its `message_type` lookup.
    """

    def founder(self, **overrides):
        fields = {
            'message_type': Message.MessageTypeChoices.FOUNDER,
            'person_name': 'Ayesha Bint e Hamid',
            'role_title': 'Founder · TEDxUMT Lahore',
            'message_body': 'First paragraph.\n\nSecond paragraph.',
            'is_visible': True,
        }
        fields.update(overrides)
        return Message.objects.create(**fields)

    def test_founder_is_a_valid_message_type(self):
        self.assertEqual(Message.MessageTypeChoices.FOUNDER, 'founder')

    def test_founder_is_fetchable_by_type(self):
        self.founder()

        response = self.client.get('/api/messages/founder/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['person_name'], 'Ayesha Bint e Hamid')

    def test_missing_founder_is_a_404_not_a_500(self):
        """The page must degrade to an empty state before anyone fills it in."""
        response = self.client.get('/api/messages/founder/')

        self.assertEqual(response.status_code, 404)

    def test_hidden_founder_is_not_public(self):
        self.founder(is_visible=False)

        self.assertEqual(self.client.get('/api/messages/founder/').status_code, 404)

    def test_founder_is_excluded_from_the_about_payload(self):
        """Otherwise the same portrait and text render on two different pages."""
        self.founder()
        Message.objects.create(
            message_type=Message.MessageTypeChoices.PRESIDENT,
            person_name='Someone Else', role_title='President',
            message_body='Hello', is_visible=True,
        )

        types = [m['message_type'] for m in self.client.get('/api/about/').json()['messages']]

        self.assertNotIn('founder', types)
        self.assertIn('president', types)

    def test_only_one_founder_can_exist(self):
        self.founder()

        with self.assertRaises(IntegrityError):
            self.founder(person_name='Someone Else')
