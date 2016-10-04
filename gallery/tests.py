import os
import sys
from tempfile import NamedTemporaryFile

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from gallery.models import Category, Image


TEMP_MEDIA_ROOT = os.path.join(
    os.path.abspath(os.path.dirname(__file__)), 'testdata'
)


def create_image(photo, category):
    category = Category.objects.create(name=category)
    return Image.objects.create(
        category=category, photo=photo, caption='This is an image'
    )


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class GalleryTests(TestCase):

    def test_image(self):
        '''
        test that image is created with correct str output
        '''
        testimg = create_image('hoop.jpg', 'category1')
        self.assertEqual(str(testimg), 'Photo id: {}'.format(testimg.id))

    def test_gallery_page(self):
        '''
        test that context is being generated correctly
        '''
        create_image('hoop.jpg', 'category1')
        response = self.client.get(reverse('gallery:gallery'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue('images' in response.context)
        self.assertTrue('categories' in response.context)

    def test_gallery_view_with_no_images(self):
        """
        If no images exist, an appropriate message should be displayed.
        """
        response = self.client.get(reverse('gallery:gallery'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Coming soon")
        self.assertQuerysetEqual(response.context['images'], [])

    def test_gallery_view_with_image(self):
        """
        If image exists, it should be displayed.
        """
        testimg = create_image('hoop.jpg', 'category1')
        response = self.client.get(reverse('gallery:gallery'))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(
            response.context['images'],
            ['<Image: Photo id: {}>'.format(testimg.id)]
        )

    def test_gallery_view_for_category(self):
        """
        Filter by category if given
        """
        testimg = create_image('hoop.jpg', 'category1')
        create_image('pole.jpg', 'category2')
        cat = Category.objects.get(name='category1')
        response = self.client.get(
            reverse('gallery:gallery'), {'category': cat.id}
        )
        # only shows category1
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(
            response.context['images'],
            ['<Image: Photo id: {}>'.format(testimg.id)]
        )

    def test_admin_upload(self):
        self.assertFalse(Image.objects.exists())
        user = User.objects.create_superuser(username='test', email='test@test.com', password='test')
        self.client.login(username=user.username, password='test')

        with open(os.path.join(settings.MEDIA_ROOT, 'hoop.jpg'), 'rb') as file:
            photo = SimpleUploadedFile(
                file.name, content=file.read()
            )

        data = {
            'name': 'test category',
            'images-TOTAL_FORMS': 1,
            'images-INITIAL_FORMS': 0,
            'images-0-photo': photo
        }
        self.client.post(reverse('admin:gallery_category_add'), data)

        self.assertTrue(Image.objects.exists())
        self.assertEqual(
            Image.objects.first().photo.name,
            'gallery/hoop.jpg'
        )
        os.unlink(os.path.join(settings.MEDIA_ROOT, 'gallery/hoop.jpg'))
        os.rmdir(os.path.join(settings.MEDIA_ROOT, 'gallery'))

    def test_admin_reupload(self):
        """
        reuploading a photos deletes the first one
        :return:
        """
        user = User.objects.create_superuser(username='test',
                                             email='test@test.com',
                                             password='test')
        self.client.login(username=user.username, password='test')

        with open(os.path.join(settings.MEDIA_ROOT, 'hoop.jpg'), 'rb') as file:
            photo = SimpleUploadedFile(
                file.name, content=file.read()
            )

        data = {
            'name': 'test category',
            'images-TOTAL_FORMS': 1,
            'images-INITIAL_FORMS': 0,
            'images-0-photo': photo
        }
        self.client.post(reverse('admin:gallery_category_add'), data)
        self.assertEqual(Image.objects.first().photo.name, 'gallery/hoop.jpg')

        cat = Category.objects.first()
        img = Image.objects.first()

        with open(os.path.join(settings.MEDIA_ROOT, 'pole.jpg'), 'rb') as file:
            photo = SimpleUploadedFile(
                file.name, content=file.read()
            )

        data = {
            'id': cat.id,
            'name': 'test category',
            'images-TOTAL_FORMS': 1,
            'images-INITIAL_FORMS': 1,
            'images-0-id': img.id,
            'images-0-photo': photo
        }
        self.client.post(reverse('admin:gallery_category_change', args=[cat.id]), data)

        self.assertFalse(
            os.path.exists(
                os.path.join(settings.MEDIA_ROOT, 'gallery/hoop.jpg')
            )
        )
        self.assertEqual(Image.objects.first().photo.name, 'gallery/pole.jpg')

        os.unlink(os.path.join(settings.MEDIA_ROOT, 'gallery/pole.jpg'))
        os.rmdir(os.path.join(settings.MEDIA_ROOT, 'gallery'))

    def test_admin_delete_photo(self):
        user = User.objects.create_superuser(username='test',
                                             email='test@test.com',
                                             password='test')
        self.client.login(username=user.username, password='test')

        with open(os.path.join(settings.MEDIA_ROOT, 'hoop.jpg'), 'rb') as file:
            photo = SimpleUploadedFile(
                file.name, content=file.read()
            )

        data = {
            'name': 'test category',
            'images-TOTAL_FORMS': 1,
            'images-INITIAL_FORMS': 0,
            'images-0-photo': photo
        }
        self.client.post(reverse('admin:gallery_category_add'), data)
        self.assertEqual(Image.objects.first().photo.name, 'gallery/hoop.jpg')

        cat = Category.objects.first()
        img = Image.objects.first()

        data = {
            'id': cat.id,
            'name': 'test category',
            'images-TOTAL_FORMS': 1,
            'images-INITIAL_FORMS': 1,
            'images-0-id': img.id,
            'images-0-DELETE': True
        }
        self.client.post(
            reverse('admin:gallery_category_change', args=[cat.id]), data)

        self.assertFalse(
            os.path.exists(
                os.path.join(settings.MEDIA_ROOT, 'gallery/hoop.jpg')
            )
        )

        os.rmdir(os.path.join(settings.MEDIA_ROOT, 'gallery'))
