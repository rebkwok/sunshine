from django.test import TestCase

from gallery.models import Category, Image

from django.core.urlresolvers import reverse

import os
import sys
from django.conf import settings


def create_image(photo, category):
    category = Category.objects.create(name=category)
    return Image.objects.create(category=category, photo=photo, caption='This is an image')

class GalleryTests(TestCase):
    def setUp(self):
        TEST_ROOT = os.path.abspath(os.path.dirname(__file__))

        self._old_MEDIA_ROOT = settings.MEDIA_ROOT

        # override MEDIA_ROOT for this test
        settings.MEDIA_ROOT = os.path.join(TEST_ROOT, 'gallery/testdata/')

    def tearDown(self):
        # reset MEDIA_ROOT
        settings.MEDIA_ROOT = self._old_MEDIA_ROOT

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
        response = self.client.get(reverse('website:gallery'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue('images' in response.context)
        self.assertTrue('categories' in response.context)

    def test_gallery_view_with_no_images(self):
        """
        If no images exist, an appropriate message should be displayed.
        """
        response = self.client.get(reverse('website:gallery'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No gallery images currently available.")
        self.assertQuerysetEqual(response.context['images'], [])

    def test_gallery_view_with_image(self):
        """
        If image exists, it should be displayed.
        """
        testimg = create_image('hoop.jpg', 'category1')
        response = self.client.get(reverse('website:gallery'))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['images'], ['<Image: Photo id: {}>'.format(testimg.id)])
