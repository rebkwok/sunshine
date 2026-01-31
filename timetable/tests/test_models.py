from datetime import time
import pytest

from model_bakery import baker

from django.core import exceptions

from ..models import SessionType, Category, Location, Venue, TimetableSession


pytestmark = pytest.mark.django_db


def test_session_type_str():
    session_type = baker.make(SessionType, name="Pole")
    assert str(session_type) == "Pole"


def test_session_type_display_on_site_requires_descriptiom():
    session_type = baker.make(
        SessionType, name="Pole", display_on_site=True, description=None
    )
    with pytest.raises(exceptions.ValidationError, match="add a description"):
        session_type.clean()


def test_venue_str():
    venue = baker.make(
        Venue,
        name="Sunshine Studio",
        location__address="1 Street",
        abbreviation="Sunshine",
    )
    assert str(venue) == "Sunshine Studio"


def test_location_str():
    location = baker.make(Location, name="foo")
    assert str(location) == "foo"


def test_category_str():
    category = baker.make(Category, name="foo")
    assert str(category) == "foo"


def test_timetable_session_str():
    ttsession = baker.make(
        TimetableSession,
        name="Pole",
        level="All levels",
        venue__abbreviation="Studio",
        session_day="01MO",
        start_time=time(13, 0),
    )
    assert str(ttsession) == "Pole (All levels), Studio, Monday 13:00"


@pytest.mark.parametrize(
    "session_type_name,show_on_timetable,expected",
    [
        ("Private", True, False),
        ("private class", True, False),
        ("Other class", True, True),
        ("Other class", False, False),
    ],
)
def test_timetable_session_never_show_private_on_timetable(
    session_type_name, show_on_timetable, expected
):
    ttsession = baker.make(
        TimetableSession,
        session_type__name=session_type_name,
        name="Class",
        level="All levels",
        venue__abbreviation="Studio",
        session_day="01MO",
        start_time=time(13, 0),
        show_on_timetable_page=show_on_timetable,
    )
    assert ttsession.show_on_timetable_page == expected
