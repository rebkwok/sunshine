import re

import pytest
from model_bakery import baker

from django.contrib.admin.sites import AdminSite

import timetable.admin as admin
from timetable.models import Venue, SessionType

from django.core.files.uploadedfile import SimpleUploadedFile


@pytest.mark.django_db
def test_venue_admin():
    venue = baker.make(
        Venue, location__address="1 Main St", location__postcode="AAA 111"
    )
    image_file = SimpleUploadedFile(
        name="venue.jpg", content=b"test", content_type="image/jpeg"
    )
    venue_with_photo = baker.make(Venue, photo=image_file)

    venue_admin = admin.VenueAdmin(Venue, AdminSite())
    query = venue_admin.get_queryset(None)
    assert query.count() == 2

    assert venue_admin.image_img(venue) == "-"
    assert re.match(
        r'<img src="\/media\/images\/venue.*\.jpg"  height="60px"/>',
        venue_admin.image_img(venue_with_photo),
    )

    assert venue_admin.addr(venue) == "1 Main St, AAA 111"


@pytest.mark.django_db
def test_session_type_admin():
    session_type = baker.make(SessionType)
    image_file = SimpleUploadedFile(
        name="session_type.jpg", content=b"test", content_type="image/jpeg"
    )
    session_type_with_photo = baker.make(SessionType, photo=image_file)

    session_type_admin = admin.SessionTypeAdmin(SessionType, AdminSite())
    query = session_type_admin.get_queryset(None)
    assert query.count() == 2

    assert session_type_admin.image_img(session_type) == "-"
    assert re.match(
        r'<img src="\/media\/images\/activity_types\/session_type.*\.jpg"  height="60px"/>',
        session_type_admin.image_img(session_type_with_photo),
    )
