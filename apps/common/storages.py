"""
Storage selection for uploaded media.

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
django-storages — which matters because django-storages is a production-only
dependency and importing it at model-definition time would break local
development, the test suite, and `manage.py` entirely.

In development the `private` alias is undefined, so both kinds fall through to
the local filesystem and behave exactly as they always have.
"""

from django.core.files.storage import InvalidStorageError, default_storage, storages


def private_media_storage():
    """The bucket for uploads that must never be publicly readable."""
    try:
        return storages['private']
    except InvalidStorageError:
        # No private alias configured (development, tests) — the local
        # filesystem is the only storage there and MEDIA_ROOT is not public.
        return default_storage
