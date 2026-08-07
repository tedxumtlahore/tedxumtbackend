"""
Create the Volunteers and Organizers groups.

Roles are Django groups rather than a custom user model: the project only needs
two coarse buckets on top of `is_staff`, and groups are already manageable from
the admin without any extra UI.

Volunteers get the check-in models only. Organizers additionally get read access
to registrations and orders. Neither group can delete anything — the check-in
log in particular is an audit trail, and staff retain full access regardless.
"""

from django.apps import apps as global_apps
from django.db import migrations

VOLUNTEERS = 'Volunteers'
ORGANIZERS = 'Organizers'

VOLUNTEER_PERMS = [
    ('ticket', 'view_ticket'),
    ('ticket', 'change_ticket'),
    ('checkinlog', 'view_checkinlog'),
    ('checkinlog', 'add_checkinlog'),
]

ORGANIZER_PERMS = VOLUNTEER_PERMS + [
    ('registration', 'view_registration'),
    ('registration', 'change_registration'),
    ('order', 'view_order'),
    ('order', 'change_order'),
]


def create_groups(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')
    ContentType = apps.get_model('contenttypes', 'ContentType')

    # Permissions for models created in this same `migrate` run do not exist
    # yet — Django creates them from a post_migrate signal that fires after
    # every migration has been applied. Without this the lookups below all miss
    # and the groups are created empty.
    _ensure_permissions_exist(apps)

    for name, perms in ((VOLUNTEERS, VOLUNTEER_PERMS), (ORGANIZERS, ORGANIZER_PERMS)):
        group, _ = Group.objects.get_or_create(name=name)
        for model, codename in perms:
            content_type = ContentType.objects.filter(
                app_label='ticketing', model=model
            ).first()
            if content_type is None:
                continue
            permission = Permission.objects.filter(
                content_type=content_type, codename=codename
            ).first()
            if permission is not None:
                group.permissions.add(permission)


def _ensure_permissions_exist(apps):
    """Force the ticketing app's model permissions into existence early."""
    from django.contrib.auth.management import create_permissions

    try:
        app_config = global_apps.get_app_config('ticketing')
    except LookupError:  # pragma: no cover — app always installed here
        return

    # create_permissions short-circuits without models_module set.
    had_models_module = app_config.models_module
    app_config.models_module = app_config.models_module or True
    try:
        create_permissions(app_config, apps=apps, verbosity=0)
    finally:
        app_config.models_module = had_models_module


def delete_groups(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.filter(name__in=[VOLUNTEERS, ORGANIZERS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('ticketing', '0001_initial'),
        ('auth', '0012_alter_user_first_name_max_length'),
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.RunPython(create_groups, delete_groups),
    ]
