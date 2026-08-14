"""
Storage selection and file naming for uploaded media.

Two kinds of upload live in this project and they have opposite exposure needs:

- **Public** — gallery images, speaker portraits, sponsor logos, blog covers.
  These exist to be looked at. Stable URLs, served straight from the bucket.
- **Private** — payment proofs. A transfer screenshot routinely shows the
  sender's wallet balance and recent transactions. `payment_proof_path` already
  randomises the filename so the path cannot be guessed; putting these in a
  separate non-public bucket means an unsigned URL does not work even if the
  path leaks.

`private_media_storage` is a *callable*, not a storage instance. Django resolves
it lazily at field instantiation, so this module never has to import
django-storages — which matters because importing a storage backend at
model-definition time would break `manage.py` entirely on any environment where
the dependency is missing. The Supabase subclasses therefore live in
`apps/common/supabase_storage.py`, which is only ever imported by name from the
`STORAGES` setting.

In development the `private` alias is undefined, so both kinds fall through to
the local filesystem and behave exactly as they always have.
"""

import re
import uuid
from pathlib import PurePosixPath

from django.core.files.storage import (
    FileSystemStorage,
    InvalidStorageError,
    default_storage,
    storages,
)
from django.utils.text import slugify

# Long names are not useful and object keys have limits. 60 characters is more
# than enough to still recognise the file in a bucket listing.
MAX_STEM_LENGTH = 60

# A plausible extension: a dot then a few alphanumerics. Anything else (no
# extension, `.tar.gz`-style doubles, or junk after a dot) is dropped rather
# than trusted, because the extension ends up in a public URL.
_EXTENSION_RE = re.compile(r'^\.[a-z0-9]{1,8}$')


def sanitized_filename(filename):
    """
    Turn whatever the organiser's laptop called the file into a safe object key.

        `My Photo (2).JPG`   -> `my-photo-2-3f9a1c2b.jpg`
        `new_02.jpg.jpeg`    -> `new_02jpg-7d1e4f80.jpeg`
        `عائشة.png`          -> `4c2b9a11.png`

    Two things matter here. Spaces, accents and punctuation survive a POSIX
    filesystem but make an ugly, percent-encoded URL and have historically
    tripped up S3-compatible services, so the stem is slugified. And a short
    random suffix makes collisions impossible without relying on the storage
    backend's own de-duplication, which differs between local disk and S3 and
    only kicks in when the backend can prove the name is already taken — a
    round trip we would rather not depend on.

    Non-Latin names slugify to nothing, so the random half stands alone rather
    than producing a bare extension.
    """
    path = PurePosixPath(str(filename).replace('\\', '/'))

    suffix = path.suffix.lower()
    if not _EXTENSION_RE.match(suffix):
        suffix = ''

    stem = slugify(path.stem)[:MAX_STEM_LENGTH].strip('-')
    unique = uuid.uuid4().hex[:8]

    return f'{stem}-{unique}{suffix}' if stem else f'{unique}{suffix}'


class MediaUploadError(Exception):
    """
    Raised when the storage backend could not accept a file.

    Defined here, in the import-light module, so that admin and view code can
    catch it without pulling in django-storages.
    """


class SanitizedNamesMixin:
    """
    Apply `sanitized_filename` to every upload, whatever the backend.

    Django calls `Storage.get_valid_name` once per save, from
    `Storage.generate_filename`, *after* the field's `upload_to` has chosen the
    directory. Hooking in here therefore renames the file while leaving the
    folder layout entirely to the models — which is why no model, migration or
    serializer has to change for this.

    `S3Boto3Storage` inherits both of those methods from Django's base
    `Storage`, so local disk and Supabase produce identical names.
    """

    def get_valid_name(self, name):
        return sanitized_filename(name)


class LocalMediaStorage(SanitizedNamesMixin, FileSystemStorage):
    """The development/fallback backend, with production's naming rules."""


def private_media_storage():
    """The bucket for uploads that must never be publicly readable."""
    try:
        return storages['private']
    except InvalidStorageError:
        # No private alias configured (development, tests) — the local
        # filesystem is the only storage there and MEDIA_ROOT is not public.
        return default_storage
