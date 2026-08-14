"""Project-wide middleware."""

import logging

from django.contrib import messages
from django.http import HttpResponseRedirect

from .storages import MediaUploadError

logger = logging.getLogger(__name__)


class MediaUploadErrorMiddleware:
    """
    Turn a failed upload into an admin message instead of a stack trace.

    The upload happens inside `Model.save()`, which the admin runs inside its
    own `transaction.atomic` block — so when object storage is unreachable the
    row is rolled back and nothing inconsistent is written. What the editor
    sees, though, is a 500 page. This catches that one exception on admin URLs
    and sends them back to the changelist with a sentence explaining what
    happened.

    Handled as middleware rather than a `ModelAdmin` mixin because every
    image-bearing model would otherwise need the same override, inlines
    included — the duplication this project's storage layer exists to avoid.

    API requests fall through untouched: DRF's handler (`api_exception_handler`)
    already renders `MediaUploadError` as a 503 in the standard error shape.

    The redirect does discard whatever was typed into the form. That is a poor
    outcome, but a rare one — it needs object storage to be down — and it beats
    a traceback with no explanation.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        if not isinstance(exception, MediaUploadError):
            return None

        # DRF renders its own response for these; only rescue the admin.
        if not request.path.startswith('/admin/'):
            return None

        logger.error('Media upload failed for admin request %s', request.path)
        messages.error(request, str(exception))

        # The atomic block inside the admin view has already rolled back, so
        # there is no half-saved record to clean up here.
        return HttpResponseRedirect(request.get_full_path())
