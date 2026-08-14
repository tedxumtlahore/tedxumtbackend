"""
Tests for the media storage layer: naming, orphan cleanup, and URL generation.

These exercise the *local* backend deliberately. The naming and cleanup code is
backend-agnostic — `S3Boto3Storage` inherits `get_valid_name` and
`generate_filename` from the same Django base class `FileSystemStorage` does —
so testing against the filesystem covers the Supabase path too, without a
network round trip or a live bucket in CI.
"""

import shutil
import tempfile
from io import StringIO
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from apps.common.cleanup import file_field_registry
from apps.common.storages import sanitized_filename
from apps.common.testing import login_as_staff
from apps.common.utils import get_file_url
from apps.team.models import Department, TeamMember

TINY_GIF = (
    b'GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!'
    b'\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
)

def photo(name='portrait.gif'):
    return SimpleUploadedFile(name, TINY_GIF, content_type='image/gif')


class MediaIsolated:
    """
    A private MEDIA_ROOT per test class.

    Uploads in these tests are real file writes. A module-level temp directory
    would work until the first class tore it down and the next one tried to
    write into it, so each class gets — and removes — its own.
    """

    @classmethod
    def setUpClass(cls):
        cls._media_root = tempfile.mkdtemp(prefix='tedxumt-storage-test-')
        cls._media_override = override_settings(MEDIA_ROOT=cls._media_root)
        cls._media_override.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls._media_override.disable()
        shutil.rmtree(cls._media_root, ignore_errors=True)


class SanitizedFilenameTest(SimpleTestCase):
    def test_slugifies_stem_and_lowercases_extension(self):
        name = sanitized_filename('My Photo (2).JPG')

        self.assertRegex(name, r'^my-photo-2-[0-9a-f]{8}\.jpg$')

    def test_double_extension_does_not_survive_verbatim(self):
        # The real bug report: `new_02.jpg.jpeg` in a production URL.
        name = sanitized_filename('new_02.jpg.jpeg')

        self.assertNotIn('.jpg.jpeg', name)
        self.assertTrue(name.endswith('.jpeg'))

    def test_non_latin_name_still_produces_a_usable_key(self):
        name = sanitized_filename('عائشة.png')

        self.assertRegex(name, r'^[0-9a-f]{8}\.png$')

    def test_missing_or_implausible_extension_is_dropped(self):
        self.assertRegex(sanitized_filename('README'), r'^readme-[0-9a-f]{8}$')
        self.assertRegex(
            sanitized_filename('archive.thisisnotanextension'),
            r'^archive-[0-9a-f]{8}$',
        )

    def test_repeated_calls_never_collide(self):
        names = {sanitized_filename('portrait.jpg') for _ in range(200)}

        self.assertEqual(len(names), 200)

    def test_path_separators_and_traversal_are_stripped(self):
        for hostile in ('../../etc/passwd.png', r'..\..\windows\evil.png'):
            with self.subTest(hostile=hostile):
                name = sanitized_filename(hostile)

                self.assertNotIn('/', name)
                self.assertNotIn('\\', name)
                self.assertNotIn('..', name)

    def test_svg_and_webp_are_preserved(self):
        # Sponsor logos are frequently SVG; the project supports them.
        self.assertTrue(sanitized_filename('logo.svg').endswith('.svg'))
        self.assertTrue(sanitized_filename('cover.webp').endswith('.webp'))


class UploadNamingTest(MediaIsolated, TestCase):
    def setUp(self):
        self.department = Department.objects.create(name='Design')

    def member(self, name='Ayesha', upload=None):
        return TeamMember.objects.create(
            name=name,
            role='Lead',
            department=self.department,
            photo=upload or photo(),
        )

    def test_upload_to_folder_is_preserved(self):
        member = self.member(upload=photo('Ayesha Portrait.gif'))

        self.assertTrue(member.photo.name.startswith('team/'))

    def test_uploaded_name_is_sanitized(self):
        member = self.member(upload=photo('Ayesha Portrait.GIF'))

        stored = Path(member.photo.name).name
        self.assertRegex(stored, r'^ayesha-portrait-[0-9a-f]{8}\.gif$')

    def test_same_filename_twice_does_not_overwrite(self):
        first = self.member(name='One', upload=photo('portrait.gif'))
        second = self.member(name='Two', upload=photo('portrait.gif'))

        self.assertNotEqual(first.photo.name, second.photo.name)
        self.assertTrue(default_storage.exists(first.photo.name))
        self.assertTrue(default_storage.exists(second.photo.name))


class OrphanCleanupTest(MediaIsolated, TestCase):
    """
    Every save here goes through `captureOnCommitCallbacks`.

    Cleanup is deliberately deferred to `transaction.on_commit`, and those
    callbacks never fire under `TestCase` — so without the wrapper these tests
    would pass while deleting nothing.
    """

    def setUp(self):
        self.department = Department.objects.create(name='Design')

    def member(self, name='Ayesha'):
        with self.captureOnCommitCallbacks(execute=True):
            return TeamMember.objects.create(
                name=name, role='Lead', department=self.department, photo=photo(),
            )

    def test_replacing_a_photo_deletes_the_old_object(self):
        member = self.member()
        original = member.photo.name

        with self.captureOnCommitCallbacks(execute=True):
            member.photo = photo('replacement.gif')
            member.save()

        self.assertNotEqual(member.photo.name, original)
        self.assertFalse(default_storage.exists(original))
        self.assertTrue(default_storage.exists(member.photo.name))

    def test_deleting_the_record_deletes_the_object(self):
        member = self.member()
        stored = member.photo.name

        with self.captureOnCommitCallbacks(execute=True):
            member.delete()

        self.assertFalse(default_storage.exists(stored))

    def test_saving_without_touching_the_photo_keeps_it(self):
        member = self.member()
        stored = member.photo.name

        with self.captureOnCommitCallbacks(execute=True):
            member.role = 'Co-Lead'
            member.save()

        self.assertTrue(default_storage.exists(stored))

    def test_object_referenced_by_another_row_is_never_deleted(self):
        """The guard that stops a shared file being destroyed by one delete."""
        first = self.member(name='One')
        shared = first.photo.name

        second = TeamMember.objects.create(
            name='Two', role='Lead', department=self.department,
        )
        # Point straight at the same key, as a fixture or data migration could.
        TeamMember.objects.filter(pk=second.pk).update(photo=shared)

        with self.captureOnCommitCallbacks(execute=True):
            first.delete()

        self.assertTrue(default_storage.exists(shared))

    @override_settings(MEDIA_DELETE_ORPHANS=False)
    def test_cleanup_can_be_switched_off(self):
        member = self.member()
        stored = member.photo.name

        with self.captureOnCommitCallbacks(execute=True):
            member.delete()

        self.assertTrue(default_storage.exists(stored))

    def test_rolled_back_save_does_not_delete_the_existing_photo(self):
        """
        The reason cleanup waits for commit.

        Callbacks captured but never executed stand in for a transaction that
        rolled back — the old file must survive, because the replacement that
        was supposed to supersede it was never written.
        """
        member = self.member()
        original = member.photo.name

        with self.captureOnCommitCallbacks(execute=False):
            member.photo = photo('replacement.gif')
            member.save()

        self.assertTrue(default_storage.exists(original))


class FileFieldRegistryTest(TestCase):
    def test_every_image_bearing_model_is_registered(self):
        """
        Guards the global promise: one storage system, every model.

        A new `ImageField` on a new model is picked up automatically, but a
        model added to a package outside `apps.` would silently miss out.
        """
        registered = {model._meta.label for model, _ in file_field_registry()}

        for label in (
            'core.HeroSection',
            'website.AboutSection',
            'website.Message',
            'events.Event',
            'speakers.Speaker',
            'team.TeamMember',
            'gallery.GalleryAlbum',
            'gallery.GalleryImage',
            'blog.BlogPost',
            'sponsors.Sponsor',
            'ticketing.Order',
        ):
            with self.subTest(model=label):
                self.assertIn(label, registered)


class FileUrlTest(SimpleTestCase):
    """`get_file_url` is the single place every serializer builds a URL."""

    class _AbsoluteUrlFile:
        """Stands in for a FieldFile backed by Supabase Storage."""

        name = 'team/ayesha-3f9a1c2b.jpg'
        url = (
            'https://project.storage.supabase.co/storage/v1/object/public/'
            'tedx-media/team/ayesha-3f9a1c2b.jpg'
        )

        def __bool__(self):
            return True

    def test_absolute_storage_url_is_returned_untouched(self):
        """
        `build_absolute_uri` leaves an already-absolute URL alone, which is what
        lets the same serializer serve local paths and bucket URLs.
        """
        request = RequestFactory().get('/api/team/')
        url = get_file_url(request, self._AbsoluteUrlFile())

        self.assertEqual(url, self._AbsoluteUrlFile.url)
        self.assertNotIn('testserver', url)

    def test_empty_file_is_none_not_a_broken_url(self):
        self.assertIsNone(get_file_url(None, None))


class AdminUploadFlowTest(MediaIsolated, TestCase):
    """
    The whole point, end to end: an editor picks a file and clicks Save, and the
    API serves it back.

    Runs against the local backend — swapping in Supabase changes where the
    bytes land and what `.url()` returns (both pinned in `SupabaseUrlShapeTest`)
    but not a single step of this flow.
    """

    def setUp(self):
        self.department = Department.objects.create(name='Design')
        login_as_staff(self.client)

    def test_adding_a_team_member_through_the_admin_stores_the_photo(self):
        response = self.client.post(
            reverse('admin:team_teammember_add'),
            {
                'name': 'Ayesha Bint e Hamid',
                'role': 'Lead',
                'department': self.department.pk,
                'bio': '',
                'email': '',
                'linkedin': '',
                'instagram': '',
                'order': 0,
                'is_visible': 'on',
                'is_active': 'on',
                'photo': photo('Ayesha Portrait.gif'),
            },
        )

        self.assertEqual(response.status_code, 302, 'Admin rejected the form.')

        member = TeamMember.objects.get(name='Ayesha Bint e Hamid')
        self.assertTrue(member.photo, 'No photo was attached.')
        self.assertTrue(member.photo.name.startswith('team/'))
        self.assertRegex(Path(member.photo.name).name, r'^ayesha-portrait-[0-9a-f]{8}\.gif$')
        self.assertTrue(default_storage.exists(member.photo.name))

    def test_api_returns_the_stored_photo_url(self):
        member = TeamMember.objects.create(
            name='Ayesha', role='Lead', department=self.department,
            photo=photo('Ayesha Portrait.gif'),
        )

        response = self.client.get('/api/team/')
        self.assertEqual(response.status_code, 200)

        photos = [
            m['photo']
            for department in response.json()['departments']
            for m in department['members']
            if m['id'] == member.pk
        ]

        self.assertEqual(len(photos), 1, 'Member missing from /api/team/.')
        # Absolute, and pointing at the object that was actually stored — the
        # frontend renders this string with no knowledge of where it came from.
        self.assertTrue(photos[0].startswith('http'))
        self.assertIn(member.photo.name, photos[0])


SUPABASE_STORAGES = {
    'default': {
        'BACKEND': 'apps.common.supabase_storage.SupabasePublicStorage',
        'OPTIONS': {
            'access_key': 'dummy',
            'secret_key': 'dummy',
            'endpoint_url': 'https://abcdefghijkl.storage.supabase.co/storage/v1/s3',
            'region_name': 'ap-southeast-1',
            'addressing_style': 'path',
            'signature_version': 's3v4',
            'default_acl': None,
            'file_overwrite': False,
            'bucket_name': 'tedx-media',
            'querystring_auth': False,
            'custom_domain': 'abcdefghijkl.supabase.co/storage/v1/object/public/tedx-media',
        },
    },
    'private': {
        'BACKEND': 'apps.common.supabase_storage.SupabasePrivateStorage',
        'OPTIONS': {
            'access_key': 'dummy',
            'secret_key': 'dummy',
            'endpoint_url': 'https://abcdefghijkl.storage.supabase.co/storage/v1/s3',
            'region_name': 'ap-southeast-1',
            'addressing_style': 'path',
            'signature_version': 's3v4',
            'default_acl': None,
            'file_overwrite': False,
            'bucket_name': 'tedx-payment-proofs',
            'querystring_auth': True,
            'querystring_expire': 600,
        },
    },
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}


@override_settings(STORAGES=SUPABASE_STORAGES)
class SupabaseUrlShapeTest(SimpleTestCase):
    """
    Both of these are silent failures: the URL is generated without contacting
    Supabase, so nothing raises — it just does not load when someone opens it.
    Building a URL costs no network, so pin the shape here.
    """

    def test_public_url_uses_the_object_path_not_the_s3_endpoint(self):
        from django.core.files.storage import storages as storage_handler

        url = storage_handler['default'].url('team/ayesha-3f9a1c2b.jpg')

        self.assertEqual(
            url,
            'https://abcdefghijkl.supabase.co/storage/v1/object/public/'
            'tedx-media/team/ayesha-3f9a1c2b.jpg',
        )
        # The S3 API path answers signed requests only — a browser gets nothing.
        self.assertNotIn('/storage/v1/s3/', url)
        self.assertNotIn('X-Amz-Signature', url)

    def test_private_url_is_signed_with_sigv4_and_expires(self):
        from django.core.files.storage import storages as storage_handler

        url = storage_handler['private'].url('payments/proofs/deadbeef.png')

        # Supabase rejects SigV2, which is what boto3 presigns with by default.
        self.assertIn('X-Amz-Signature', url)
        self.assertIn('X-Amz-Credential', url)
        self.assertNotIn('AWSAccessKeyId', url)
        self.assertIn('X-Amz-Expires=600', url)

    def test_private_bucket_is_not_the_public_one(self):
        from django.core.files.storage import storages as storage_handler

        self.assertNotEqual(
            storage_handler['private'].bucket_name,
            storage_handler['default'].bucket_name,
        )


class SyncCommandTest(MediaIsolated, TestCase):
    def test_command_refuses_to_run_without_a_bucket(self):
        """Without MEDIA_BUCKET the destination is local disk — a no-op copy."""
        out = StringIO()
        call_command('sync_media_to_storage', stdout=out)

        self.assertIn('MEDIA_BUCKET is not set', out.getvalue())

    def test_storage_save_preserves_an_exact_name(self):
        """
        The property the migration utility depends on: `Storage.save` does not
        re-run the sanitiser, so existing database paths stay valid.
        """
        name = 'team/new_02.jpg.jpeg'
        written = default_storage.save(name, ContentFile(TINY_GIF))
        self.addCleanup(default_storage.delete, written)

        self.assertEqual(written, name)
