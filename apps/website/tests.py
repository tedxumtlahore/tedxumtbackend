from django.apps import apps as django_apps
from django.test import RequestFactory, SimpleTestCase, TestCase

from .models import AboutSection, CoreValue, Founder, Message
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
    """The Founder page is its own model, served at /api/founder/."""

    def founder(self, **overrides):
        fields = {
            'name': 'Ayesha Bint e Hamid',
            'role_title': 'Founder · TEDxUMT Lahore',
            'story': 'First paragraph.\n\nSecond paragraph.',
            'is_visible': True,
        }
        fields.update(overrides)
        return Founder.objects.create(**fields)

    def test_founder_is_served(self):
        self.founder()

        response = self.client.get('/api/founder/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['name'], 'Ayesha Bint e Hamid')
        self.assertIn('Second paragraph.', response.json()['story'])

    def test_missing_founder_is_a_404_not_a_500(self):
        """The page must degrade to an empty state before anyone fills it in."""
        self.assertEqual(self.client.get('/api/founder/').status_code, 404)

    def test_hidden_founder_is_not_public(self):
        self.founder(is_visible=False)

        self.assertEqual(self.client.get('/api/founder/').status_code, 404)

    def test_founder_is_no_longer_a_message_type(self):
        """Two places to edit one thing is the confusion this model removed."""
        self.assertNotIn('founder', Message.MessageTypeChoices.values)

    def test_admin_allows_only_one_founder(self):
        from django.contrib import admin as django_admin

        model_admin = django_admin.site._registry[Founder]
        request = RequestFactory().get('/admin/')

        self.assertTrue(model_admin.has_add_permission(request))
        self.founder()
        self.assertFalse(model_admin.has_add_permission(request))


class FounderMigrationTests(TestCase):
    """
    The data migration that moves an existing founder Message into Founder.

    Production already has a founder filled in as a Message, so this runs
    against real content on the next deploy — worth exercising rather than
    trusting. The functions only use `apps.get_model`, so handing them the real
    registry tests the logic exactly as the migration runs it.
    """

    def setUp(self):
        from importlib import import_module

        self.mig = import_module(
            'apps.website.migrations.0005_move_founder_message_to_founder'
        )

    def message(self, **overrides):
        fields = {
            'message_type': 'founder',
            'person_name': 'Ayesha Bint e Hamid',
            'role_title': 'Founder',
            'message_body': 'Para one.\n\nPara two.',
            'photo': 'founder/portrait-abc12345.jpg',
            'is_visible': True,
        }
        fields.update(overrides)
        return Message.objects.create(**fields)

    def test_founder_message_is_copied_and_removed(self):
        self.message()

        self.mig.message_to_founder(django_apps, None)

        founder = Founder.objects.get()
        self.assertEqual(founder.name, 'Ayesha Bint e Hamid')
        self.assertIn('Para two.', founder.story)
        # The photo is carried across by name, so the object already in
        # Supabase Storage is reused rather than needing a re-upload.
        self.assertEqual(founder.photo.name, 'founder/portrait-abc12345.jpg')
        self.assertFalse(Message.objects.filter(message_type='founder').exists())

    def test_nothing_happens_without_a_founder_message(self):
        self.mig.message_to_founder(django_apps, None)

        self.assertFalse(Founder.objects.exists())

    def test_an_existing_founder_is_never_clobbered(self):
        Founder.objects.create(name='Real Edit', story='Kept')
        self.message()

        self.mig.message_to_founder(django_apps, None)

        self.assertEqual(Founder.objects.get().name, 'Real Edit')

    def test_reverse_puts_the_message_back(self):
        self.message()
        self.mig.message_to_founder(django_apps, None)

        self.mig.founder_to_message(django_apps, None)

        self.assertEqual(
            Message.objects.get(message_type='founder').person_name,
            'Ayesha Bint e Hamid',
        )
        self.assertFalse(Founder.objects.exists())
