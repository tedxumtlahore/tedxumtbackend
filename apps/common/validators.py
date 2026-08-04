from urllib.parse import urlparse

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def validate_http_url(value):
    parsed_url = urlparse(value)
    if parsed_url.scheme not in {'http', 'https'} or not parsed_url.netloc:
        raise ValidationError(_('Enter a valid http or https URL.'))


def validate_file_size(value, max_size_mb=5):
    max_size_bytes = max_size_mb * 1024 * 1024
    if value.size > max_size_bytes:
        raise ValidationError(
            _('File size must be %(max_size)s MB or smaller.'),
            params={'max_size': max_size_mb},
        )
