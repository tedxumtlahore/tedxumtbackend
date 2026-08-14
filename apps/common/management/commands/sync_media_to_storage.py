"""
Copy media that still lives on local disk up to the configured storage.

Existing rows hold paths like `team/new_02.jpg.jpeg`. Those paths stay exactly
as they are — the same key is written into the bucket, so every serializer
starts returning a working URL for records that were uploaded before Supabase
Storage was switched on, with no database change and no migration.

Deliberately conservative:

- **It reports, it does not act.** `--apply` is required to write anything.
- **It never deletes.** The local copy is left where it is, so the command can
  be run again, and a bad run costs nothing but bucket space.
- **It never overwrites.** Anything already in the bucket is skipped, so it is
  safe to re-run after a partial failure.
- **It never touches the database.** Names are preserved, so there is nothing
  to update.

    python manage.py sync_media_to_storage              # report only
    python manage.py sync_media_to_storage --apply
    python manage.py sync_media_to_storage --apply --model team.TeamMember
"""

from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError

from apps.common.cleanup import file_field_registry


class Command(BaseCommand):
    help = 'Upload media still on local disk to the configured storage backend.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply',
            action='store_true',
            help='Actually upload. Without this the command only reports.',
        )
        parser.add_argument(
            '--model',
            help='Limit to one model, as app_label.ModelName (case-insensitive).',
        )
        parser.add_argument(
            '--source',
            help='Directory holding the local files. Defaults to MEDIA_ROOT.',
        )

    def handle(self, *args, **options):
        apply_changes = options['apply']
        source = Path(options['source'] or settings.MEDIA_ROOT)
        wanted = (options['model'] or '').lower() or None

        if not source.is_dir():
            raise CommandError(f'Source directory does not exist: {source}')

        if not getattr(settings, 'MEDIA_BUCKET', ''):
            self.stdout.write(self.style.WARNING(
                'MEDIA_BUCKET is not set, so the destination storage is the '
                'local filesystem — this run would copy files onto themselves. '
                'Configure Supabase Storage first.'
            ))
            return

        targets = file_field_registry()
        if wanted:
            targets = [m for m in targets if m[0]._meta.label_lower == wanted]
            if not targets:
                raise CommandError(f'No model with file fields matches {options["model"]!r}.')

        uploaded = skipped = missing = failed = 0

        for model, field_names in targets:
            for instance in model._base_manager.iterator():
                for field_name in field_names:
                    field_file = getattr(instance, field_name, None)
                    if not field_file or not field_file.name:
                        continue

                    name = field_file.name
                    storage = field_file.storage
                    label = f'{model._meta.label}#{instance.pk}.{field_name}'

                    try:
                        if storage.exists(name):
                            skipped += 1
                            self.stdout.write(f'  = {name}  ({label}) already in storage')
                            continue
                    except Exception as exc:
                        failed += 1
                        self.stdout.write(self.style.ERROR(
                            f'  ! {name}  ({label}) could not be checked: {exc}'
                        ))
                        continue

                    local_path = source / name
                    if not local_path.is_file():
                        missing += 1
                        self.stdout.write(self.style.WARNING(
                            f'  ? {name}  ({label}) not found at {local_path}'
                        ))
                        continue

                    if not apply_changes:
                        uploaded += 1
                        self.stdout.write(f'  + {name}  ({label}) would upload')
                        continue

                    try:
                        with local_path.open('rb') as handle:
                            # `Storage.save` does not re-run the name sanitiser,
                            # and the key is known not to exist, so the stored
                            # name comes back unchanged and the database row
                            # keeps pointing at the right object.
                            written = storage.save(name, File(handle))
                    except Exception as exc:
                        failed += 1
                        self.stdout.write(self.style.ERROR(
                            f'  ! {name}  ({label}) upload failed: {exc}'
                        ))
                        continue

                    if written != name:
                        # Should be unreachable; report it rather than leaving a
                        # row silently pointing at the wrong object.
                        failed += 1
                        self.stdout.write(self.style.ERROR(
                            f'  ! {name}  ({label}) stored as {written} — '
                            'the database still refers to the original name.'
                        ))
                        continue

                    uploaded += 1
                    self.stdout.write(self.style.SUCCESS(f'  + {name}  ({label}) uploaded'))

        verb = 'Uploaded' if apply_changes else 'Would upload'
        self.stdout.write('')
        self.stdout.write(
            f'{verb}: {uploaded}   already present: {skipped}   '
            f'missing locally: {missing}   failed: {failed}'
        )

        if not apply_changes and uploaded:
            self.stdout.write(self.style.WARNING(
                'Nothing was written. Re-run with --apply to upload.'
            ))
        if apply_changes:
            self.stdout.write(
                'Local files were left in place; nothing was deleted.'
            )
