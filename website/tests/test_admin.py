import re

import pytest
from model_bakery import baker

from django.contrib.admin.sites import AdminSite

import website.admin as admin
from website.models import GalleryImage, TeamMember

from django.core.files.uploadedfile import SimpleUploadedFile


@pytest.mark.django_db
def test_gallery_image_admin():
    gallery_image = baker.make(GalleryImage)
    image_file = SimpleUploadedFile(name="image.jpg", content=b'test', content_type="image/jpeg")
    gallery_image_with_photo = baker.make(GalleryImage, photo=image_file)

    gallery_image_admin = admin.GalleryImageAdmin(GalleryImage, AdminSite())
    query = gallery_image_admin.get_queryset(None)
    assert query.count() == 2
    
    assert gallery_image_admin.image_img(gallery_image) == "-"
    assert re.match(rf'<img src="\/media\/images\/gallery\/image.*\.jpg"  height="60px"/>', gallery_image_admin.image_img(gallery_image_with_photo))


@pytest.mark.django_db
def test_team_member_admin():
    team_member = baker.make(TeamMember)
    image_file = SimpleUploadedFile(name="image.jpg", content=b'test', content_type="image/jpeg")
    team_member_with_photo = baker.make(TeamMember, photo=image_file)

    team_member_admin = admin.TeamMemberAdmin(TeamMember, AdminSite())
    query = team_member_admin.get_queryset(None)
    assert query.count() == 2

    assert team_member_admin.image_img(team_member) == "-"
    assert re.match(rf'<img src="\/media\/images\/team\/image.*\.jpg"  height="60px"/>', team_member_admin.image_img(team_member_with_photo))
