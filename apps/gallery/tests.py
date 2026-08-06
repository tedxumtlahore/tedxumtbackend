import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from .models import GalleryAlbum, GalleryImage

# Smallest valid GIF — enough for ImageField validation without shipping a fixture.
TINY_GIF = (
    b'GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!'
    b'\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
)

# Uploads in tests are real file writes. Without this they land in the project's
# media/ directory and accumulate there forever.
TEMP_MEDIA_ROOT = tempfile.mkdtemp(prefix='tedxumt-test-media-')


def upload(name='test.gif'):
    return SimpleUploadedFile(name, TINY_GIF, content_type='image/gif')


class MediaIsolatedTestCase:
    """Mixin: route uploads to a throwaway directory and delete it afterwards."""

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class GalleryModelTests(MediaIsolatedTestCase, TestCase):
    def test_album_slug_is_generated_and_unique(self):
        first = GalleryAlbum.objects.create(title='Resonance 2026')
        second = GalleryAlbum.objects.create(title='Resonance 2026')

        self.assertEqual(first.slug, 'resonance-2026')
        self.assertEqual(second.slug, 'resonance-2026-1')

    def test_image_str_falls_back_to_album_title(self):
        album = GalleryAlbum.objects.create(title='Genesis 2024')
        image = GalleryImage.objects.create(album=album, image=upload())

        self.assertIn('Genesis 2024', str(image))

    def test_deleting_album_cascades_to_images(self):
        album = GalleryAlbum.objects.create(title='Convergence 2025')
        GalleryImage.objects.create(album=album, image=upload())

        album.delete()

        self.assertEqual(GalleryImage.objects.count(), 0)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class GalleryAPITests(MediaIsolatedTestCase, APITestCase):
    def setUp(self):
        self.album = GalleryAlbum.objects.create(title='Resonance 2026')
        self.photo = GalleryImage.objects.create(
            album=self.album, image=upload(), caption='Opening keynote', order=1
        )
        self.video = GalleryImage.objects.create(
            album=self.album,
            image=upload(),
            caption='Highlight reel',
            media_type=GalleryImage.MediaTypeChoices.VIDEO,
            video_url='https://youtube.com/watch?v=abc',
            order=2,
        )
        GalleryImage.objects.create(album=self.album, image=upload(), is_visible=False)

    def test_feed_returns_only_visible_images(self):
        response = self.client.get(reverse('api-gallery'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(len(response.data['media_types']), 3)

    def test_feed_filters_by_media_type(self):
        response = self.client.get(reverse('api-gallery'), {'media_type': 'video'})

        self.assertEqual([i['caption'] for i in response.data['results']], ['Highlight reel'])

    def test_feed_hides_images_of_a_hidden_album(self):
        self.album.is_visible = False
        self.album.save()

        response = self.client.get(reverse('api-gallery'))

        self.assertEqual(response.data['results'], [])

    def test_album_detail_nests_visible_images(self):
        response = self.client.get(f'/api/gallery-albums/{self.album.slug}/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['images']), 2)
        self.assertEqual(response.data['image_count'], 2)

    def test_alt_text_falls_back_to_caption(self):
        response = self.client.get(reverse('api-gallery'))
        first = response.data['results'][0]

        self.assertEqual(first['resolved_alt_text'], 'Opening keynote')

    def test_anonymous_users_cannot_upload_images(self):
        response = self.client.post('/api/gallery-images/', {
            'album': self.album.pk, 'image_upload': upload(),
        })

        self.assertEqual(response.status_code, 403)
