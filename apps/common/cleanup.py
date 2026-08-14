"""
Remove stored objects that nothing points at any more.

Django never deletes the underlying file when a `FileField` is overwritten or
its row is removed — the object just sits in the bucket, unreferenced and
billable, forever. Re-cropping one speaker portrait a dozen times leaves a
dozen dead objects.

Three rules keep this from ever destroying a live image:

1. **Nothing is deleted until the transaction commits.** These signals fire
   inside the transaction, so deleting there would discard the file even when
   the save is rolled back moments later. Every delete is deferred with
   `transaction.on_commit`. (Which means tests must wrap saves in
   `captureOnCommitCallbacks(execute=True)`, exactly like the email tests.)
2. **Nothing is deleted while another row references it.** Names are made
   unique on upload, so sharing should be impossible — but a fixture, a data
   migration or a hand-edited row can still produce two records pointing at one
   object, and the cost of checking is one cheap query per registered field.
   `_base_manager` is used deliberately: a soft-deleted (`is_active=False`) row
   still counts as a reference.
3. **A failed delete is never fatal.** Losing a stale object matters far less
   than a 500 on an admin save, so storage errors are logged and swallowed.

Set `MEDIA_DELETE_ORPHANS=False` to switch the whole thing off; uploads then
accumulate exactly as they did before.
"""

import logging

from django.apps import apps as django_apps
from django.conf import settings
from django.db import transaction
from django.db.models import FileField, Q
from django.db.models.signals import post_delete, post_save, pre_save

logger = logging.getLogger(__name__)

# Attribute used to carry the superseded files from pre_save to post_save. It
# has to be the *old* values, which are gone from the instance by post_save.
_STASH = '_media_orphans_pending'

# [(model, ('photo', 'banner_image', ...)), ...] — populated by
# `register_media_cleanup` and used for the "is anything else using this?" check.
_REGISTRY = []


def file_field_registry():
    """
    Every project model that stores a file, as `[(model, ('photo', ...)), ...]`.

    Built once at startup by `register_media_cleanup`. The media sync command
    uses it so that a newly added `ImageField` is covered without anyone having
    to remember to list it.
    """
    return list(_REGISTRY)


def _file_field_names(model):
    return tuple(
        field.name
        for field in model._meta.get_fields()
        if isinstance(field, FileField)
    )


def _enabled():
    # Read at call time, not import time, so `override_settings` works.
    return getattr(settings, 'MEDIA_DELETE_ORPHANS', True)


def _still_referenced(name, origin_model, origin_pk):
    """Is any row — in any model — still pointing at this object?"""
    for model, field_names in _REGISTRY:
        query = Q()
        for field_name in field_names:
            query |= Q(**{field_name: name})

        queryset = model._base_manager.filter(query)
        if model is origin_model and origin_pk is not None:
            queryset = queryset.exclude(pk=origin_pk)

        if queryset.exists():
            return True

    return False


def _delete_if_orphaned(storage, name, origin_model, origin_pk):
    if not name:
        return

    if _still_referenced(name, origin_model, origin_pk):
        logger.debug('Keeping %s — another record still references it.', name)
        return

    try:
        storage.delete(name)
    except Exception:
        # An orphaned object costs a fraction of a cent. An exception here
        # would cost the editor their save.
        logger.warning('Could not delete stored file %s', name, exc_info=True)
    else:
        logger.info('Deleted orphaned file %s', name)


def _schedule_delete(field_file, origin_model, origin_pk):
    if not field_file:
        return

    # Capture the storage and name now: the FieldFile is bound to an instance
    # that may be mutated or garbage before the commit hook runs.
    storage, name = field_file.storage, field_file.name
    transaction.on_commit(
        lambda: _delete_if_orphaned(storage, name, origin_model, origin_pk)
    )


def stash_replaced_files(sender, instance, **kwargs):
    """pre_save: note which files this save is about to orphan."""
    setattr(instance, _STASH, [])

    if not _enabled() or instance.pk is None:
        return

    try:
        previous = sender._base_manager.get(pk=instance.pk)
    except sender.DoesNotExist:
        return  # An insert with an explicit pk — nothing is being replaced.

    superseded = []
    for field_name in _file_field_names(sender):
        old_file = getattr(previous, field_name, None)
        new_file = getattr(instance, field_name, None)
        if old_file and old_file.name != getattr(new_file, 'name', None):
            superseded.append(old_file)

    setattr(instance, _STASH, superseded)


def purge_replaced_files(sender, instance, **kwargs):
    """post_save: the replacement is committed, so the old file can go."""
    superseded = getattr(instance, _STASH, None) or []
    setattr(instance, _STASH, [])

    for field_file in superseded:
        _schedule_delete(field_file, sender, instance.pk)


def purge_files_of_deleted_row(sender, instance, **kwargs):
    """post_delete: the row is gone, so its files have no owner."""
    if not _enabled():
        return

    for field_name in _file_field_names(sender):
        _schedule_delete(getattr(instance, field_name, None), sender, instance.pk)


def register_media_cleanup():
    """
    Wire the signals for every project model that stores a file.

    Called from `CommonConfig.ready()`. Only this project's models are touched
    — Django's own tables and third-party apps are left alone.
    """
    _REGISTRY.clear()

    for model in django_apps.get_models():
        if not model.__module__.startswith('apps.'):
            continue

        field_names = _file_field_names(model)
        if not field_names:
            continue

        _REGISTRY.append((model, field_names))

        label = model._meta.label_lower
        pre_save.connect(
            stash_replaced_files, sender=model,
            dispatch_uid=f'media-cleanup-stash-{label}',
        )
        post_save.connect(
            purge_replaced_files, sender=model,
            dispatch_uid=f'media-cleanup-purge-{label}',
        )
        post_delete.connect(
            purge_files_of_deleted_row, sender=model,
            dispatch_uid=f'media-cleanup-delete-{label}',
        )
