from django.test import SimpleTestCase

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
