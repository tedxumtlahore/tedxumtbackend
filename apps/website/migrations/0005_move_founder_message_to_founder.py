"""
Move the founder out of `Message` and into the `Founder` model.

The founder was briefly a fourth `message_type`. Anyone who filled that in
before this migration should not have to type it again, so the row is copied
across — `photo` included, by name, so the object already in Supabase Storage
is reused rather than re-uploaded.

The old Message row is then removed, because leaving it would mean two places
in the admin claiming to edit the same thing. `reverse` puts it back.

Deletes here are safe from the media cleanup in apps/common/cleanup.py: its
signals are connected to the real model classes, and migrations operate on
historical ones, so nothing fires and the photo is never touched.
"""

from django.db import migrations

FOUNDER = 'founder'


def message_to_founder(apps, schema_editor):
    Message = apps.get_model('website', 'Message')
    Founder = apps.get_model('website', 'Founder')

    if Founder.objects.exists():
        return  # Already populated — never clobber a real edit.

    message = Message.objects.filter(message_type=FOUNDER).first()
    if message is None:
        return

    Founder.objects.create(
        name=message.person_name,
        role_title=message.role_title or 'Founder · TEDxUMT Lahore',
        story=message.message_body,
        photo=message.photo.name or '',
        is_visible=message.is_visible,
        is_active=message.is_active,
    )
    message.delete()


def founder_to_message(apps, schema_editor):
    Message = apps.get_model('website', 'Message')
    Founder = apps.get_model('website', 'Founder')

    founder = Founder.objects.first()
    if founder is None or Message.objects.filter(message_type=FOUNDER).exists():
        return

    Message.objects.create(
        message_type=FOUNDER,
        person_name=founder.name,
        role_title=founder.role_title,
        message_body=founder.story,
        photo=founder.photo.name or '',
        is_visible=founder.is_visible,
        is_active=founder.is_active,
    )
    founder.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0004_founder_alter_message_options_and_more'),
    ]

    operations = [
        migrations.RunPython(message_to_founder, founder_to_message),
    ]
