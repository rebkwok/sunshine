import os
from model_mommy import mommy

from django.contrib.admin import AdminSite
from django.core.urlresolvers import reverse
from django.test import override_settings, TestCase

from timetable import admin
from timetable.models import TimetableSession, SessionType, Instructor, Venue


TEMP_MEDIA_FOLDER = os.path.join(
            os.path.abspath(os.path.dirname(__file__)), 'timetable/testdata/'
        )


class TimetableListViewTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.url = reverse('timetable:timetable')
        cls.pole = mommy.make(SessionType, name='pole')
        cls.hoop = mommy.make(SessionType, name='hoop')
        cls.venue1 = mommy.make(Venue, abbreviation='venue1')
        cls.venue2 = mommy.make(Venue, abbreviation='venue2')
        mommy.make(
            TimetableSession, session_type=cls.pole, venue=cls.venue1,
            cost=4, _quantity=2
        )
        mommy.make(
            TimetableSession, session_type=cls.pole, venue=cls.venue2,
            cost=3.5, _quantity=2
        )
        mommy.make(
            TimetableSession, session_type=cls.hoop, venue=cls.venue1,
            cost=4, _quantity=2
        )
        mommy.make(
            TimetableSession, session_type=cls.hoop, venue=cls.venue2,
            cost=3.5, _quantity=2
        )

    def test_get_timetable_view(self):
        self.assertEqual(TimetableSession.objects.count(), 8)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context_data['timetable_sessions']), 8)

    def test_filters(self):
        self.assertEqual(TimetableSession.objects.count(), 8)
        resp = self.client.get(
            self.url, {'filtered_session_type': self.pole.id}
        )
        self.assertEqual(len(resp.context_data['timetable_sessions']), 4)
        for tt in resp.context_data['timetable_sessions']:
            self.assertEqual(tt.session_type, self.pole)

        resp = self.client.get(
            self.url, {'filtered_venue': self.venue1.abbreviation}
        )
        self.assertEqual(len(resp.context_data['timetable_sessions']), 4)
        for tt in resp.context_data['timetable_sessions']:
            self.assertEqual(tt.venue, self.venue1)

        resp = self.client.get(
            self.url,
            {
                'filtered_session_type': self.hoop.id,
                'filtered_venue': self.venue2.abbreviation
            }
        )
        self.assertEqual(len(resp.context_data['timetable_sessions']), 2)
        for tt in resp.context_data['timetable_sessions']:
            self.assertEqual(tt.session_type, self.hoop)
            self.assertEqual(tt.venue, self.venue2)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_FOLDER)
class AdminTests(TestCase):

    def test_instructor_admin_display(self):
        instructor = mommy.make(Instructor)

        instructor_admin = admin.InstructorAdmin(Instructor, AdminSite())
        instructor_query = instructor_admin.get_queryset(None)[0]
        self.assertFalse(instructor_admin.has_photo(instructor_query))

        instructor.photo = 'photo.jpg'
        instructor.save()
        instructor_admin = admin.InstructorAdmin(Instructor, AdminSite())
        instructor_query = instructor_admin.get_queryset(None)[0]
        self.assertTrue(instructor_admin.has_photo(instructor_query))

    def test_session_type_admin_display(self):
        session_type = mommy.make(SessionType)

        session_type_admin = admin.SessionTypeAdmin(SessionType, AdminSite())
        st_query = session_type_admin.get_queryset(None)[0]
        self.assertFalse(session_type_admin.has_photo(st_query))

        session_type.photo = 'photo.jpg'
        session_type.save()
        session_type_admin = admin.SessionTypeAdmin(SessionType, AdminSite())
        st_query = session_type_admin.get_queryset(None)[0]
        self.assertTrue(session_type_admin.has_photo(st_query))


class ModelTests(TestCase):

    def test_instructor_str(self):
        instructor = mommy.make(Instructor, name="Donald Duck")
        self.assertEqual(str(instructor), "Donald Duck")

    def test_session_type_str(self):
        session_type = mommy.make(SessionType, name="Pole")
        self.assertEqual(str(session_type), "Pole")

    def test_venue_str(self):
        venue = mommy.make(
            Venue, venue="Carousel Fitness Studio",
            address="7 Preston Crescent, Inverkeithing",
            abbreviation="Inverkeithing"
        )
        self.assertEqual(str(venue), "Carousel Fitness Studio")


