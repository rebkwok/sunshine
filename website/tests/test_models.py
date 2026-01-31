import re

import pytest
from model_bakery import baker

from django.core.files.uploadedfile import SimpleUploadedFile

from website.models import GalleryCategory, GalleryImage


@pytest.mark.django_db
def test_gallery_category_str():
    gallery_cat = baker.make(GalleryCategory, name="Test cat")
    assert str(gallery_cat) == "Test cat"


@pytest.mark.django_db
def test_gallery_image_str():
    gallery_cat = baker.make(GalleryCategory, name="Test cat")
    gallery_im = baker.make(GalleryImage, category=gallery_cat)
    assert str(gallery_im) == "Test cat - "

    image_file = SimpleUploadedFile(
        name="image.jpg", content=b"test", content_type="image/jpeg"
    )
    gallery_im_with_photo = baker.make(
        GalleryImage, category=gallery_cat, photo=image_file
    )
    re.match(r"Test cat - images\/gallery\/image.*\.jpg", str(gallery_im_with_photo))
