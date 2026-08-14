"""
Supabase Storage backends.

Supabase Storage exposes an S3-compatible API, so `django-storages`' mature,
well-tested `S3Boto3Storage` drives it directly — there is no need for a
hand-written backend on top of the `supabase-py` client, and no second set of
credentials. Everything Supabase-specific (path addressing, no object ACLs) is
configured in `tedxumt/settings/base.py`.

**This module must only ever be imported by name from the `STORAGES` setting.**
Django resolves those strings lazily, which keeps `import storages.backends...`
out of the model-definition import path. `apps/common/storages.py` is the
import-light module that models and admin code use.

The two classes differ only in intent; their behaviour comes from the options
the settings hand them (public and unsigned vs private and signed). They exist
as named classes so the settings read clearly and so `_save` error handling is
shared.
"""

import logging

from storages.backends.s3boto3 import S3Boto3Storage

from .storages import MediaUploadError, SanitizedNamesMixin

logger = logging.getLogger(__name__)


class SupabaseStorageMixin(SanitizedNamesMixin):
    """Sanitised names, plus an upload failure that says what actually broke."""

    def _save(self, name, content):
        try:
            return super()._save(name, content)
        except Exception as exc:
            # Django admin turns an unhandled exception into a 500, and the
            # model row is never written because the upload happens inside
            # `Model.save()` — so a failure here cannot leave a database record
            # pointing at a file that does not exist. What it *would* leave is
            # an editor staring at a stack trace, so name the bucket and the
            # key in the log (never the credentials, which live only in the
            # boto3 client) and re-raise something the admin can present.
            logger.exception(
                'Upload to Supabase Storage failed: bucket=%s key=%s',
                self.bucket_name,
                name,
            )
            raise MediaUploadError(
                f'Could not upload “{name}” to media storage. '
                'The file was not saved. Please try again — if this keeps '
                'happening, the storage credentials or bucket may need '
                'attention.'
            ) from exc


class SupabasePublicStorage(SupabaseStorageMixin, S3Boto3Storage):
    """Gallery, portraits, logos, blog covers — served straight from the bucket."""


class SupabasePrivateStorage(SupabaseStorageMixin, S3Boto3Storage):
    """Payment proofs — reachable only through a short-lived signed URL."""
