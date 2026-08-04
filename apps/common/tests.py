from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase

from .models import StatusChoices
from .validators import validate_file_size, validate_http_url


class CommonValidatorsTest(SimpleTestCase):
    def test_validate_http_url_accepts_http_and_https(self):
        validate_http_url('https://example.com')
        validate_http_url('http://example.com/path')

    def test_validate_http_url_rejects_invalid_scheme(self):
        with self.assertRaises(ValidationError):
            validate_http_url('ftp://example.com')

    def test_validate_file_size_rejects_oversized_upload(self):
        upload = SimpleUploadedFile('test.jpg', b'a', content_type='image/jpeg')

        with self.assertRaises(ValidationError):
            validate_file_size(upload, max_size_mb=0)


class StatusChoicesTest(SimpleTestCase):
    def test_status_choices_include_expected_values(self):
        self.assertEqual(StatusChoices.DRAFT, 'draft')
        self.assertEqual(StatusChoices.PUBLISHED, 'published')
