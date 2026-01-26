import pytz
import pytest

from datetime import datetime
from datetime import timezone as dt_timezone

from unittest.mock import patch
from model_bakery import baker

from django.contrib.auth.models import User
from django.urls import reverse
from django.test import TestCase

from booking.models import Event
from timetable.models import TimetableSession, SessionType, Venue, Location


pytestmark = pytest.mark.django_db


class TimetableListViewTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.url = reverse('timetable:timetable')
        cls.pole = baker.make(SessionType, name='pole')
        cls.hoop = baker.make(SessionType, name='hoop')
        cls.venue1 = baker.make(Venue, abbreviation='venue1')
        cls.venue2 = baker.make(Venue, abbreviation='venue2')
        baker.make(
            TimetableSession, session_type=cls.pole, venue=cls.venue1,
            cost=4, _quantity=2
        )
        baker.make(
            TimetableSession, session_type=cls.pole, venue=cls.venue2,
            cost=3.5, _quantity=2
        )
        baker.make(
            TimetableSession, session_type=cls.hoop, venue=cls.venue1,
            cost=4, _quantity=2
        )
        baker.make(
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


def test_timetable_list_tab_(client):
    location1 = baker.make(Location, name="l1")
    location2 = baker.make(Location, name="l2")
    ttsession1 = baker.make(TimetableSession, venue__location=location1)
    ttsession2 = baker.make(TimetableSession, venue__location=location2, show_on_timetable_page=False)

    # One active location, tab set to first location that's active (not 0, as all locations tab isn't shown)
    resp =  client.get(reverse('timetable:timetable'))
    assert resp.context_data['tab'] == 1

    # non-int tab, default to whatever the default tab is
    resp =  client.get(reverse('timetable:timetable') + "?tab=foo")
    assert resp.context_data['tab'] == 1

    ttsession2.show_on_timetable_page = True
    ttsession2.save()

    # Two active locations, tab set to 0
    resp =  client.get(reverse('timetable:timetable'))
    assert resp.context_data['tab'] == 0

     # non-int tab, default to whatever the default tab is
    resp =  client.get(reverse('timetable:timetable') + "?tab=foo")
    assert resp.context_data['tab'] == 0


class UploadTimetableTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.url = reverse('admin:upload_timetable')
        cls.superuser = User.objects.create_superuser(
            username='superuser', email='test@test.com', password='test'
        )
        cls.staff_user = User.objects.create_user(
            username='staff', email='test@test.com', password='test', is_staff=True
        )
        cls.user = User.objects.create_user(
            username='test', email='test@test.com', password='test'
        )
    
    def test_only_superuser(self):
        self.client.force_login(self.staff_user)
        resp = self.client.get(self.url)
        assert resp.status_code == 302
        assert resp.url == reverse("admin:index")

        self.client.force_login(self.superuser)
        resp = self.client.get(self.url)
        assert resp.status_code == 200

    @patch('timetable.forms.timezone')
    def test_events_are_created(self, mock_tz):
        self.client.login(username=self.superuser.username, password='test')
        mock_tz.now.return_value = datetime(
            2015, 6, 1, 0, 0, tzinfo=dt_timezone.utc
        )
        baker.make_recipe('booking.mon_session', _quantity=5)
        self.assertEqual(Event.objects.count(), 0)
        form_data = {
            'start_date': 'Mon 08 Jun 2015',
            'end_date': 'Sun 14 Jun 2015',
            'sessions': [session.id for session in TimetableSession.objects.all()]
        }
        self.client.post(self.url, data=form_data)
        self.assertEqual(Event.objects.count(), 5)
        for session in TimetableSession.objects.all():
            Event.objects.filter(name='{} ({})'.format(session.name, session.level)).exists()

        self.assertEqual(Event.objects.filter(event_type='regular_session').count(), 5)

    @patch('timetable.forms.timezone')
    def test_does_not_create_duplicate_sessions(self, mock_tz):
        self.client.login(username=self.superuser.username, password='test')
        mock_tz.now.return_value = datetime(
            2015, 6, 1, 0, 0, tzinfo=dt_timezone.utc
        )
        baker.make_recipe('booking.mon_session', _quantity=5)
        self.assertEqual(Event.objects.count(), 0)
        form_data = {
            'start_date': 'Mon 08 Jun 2015',
            'end_date': 'Sun 14 Jun 2015',
            'sessions': [session.id for session in TimetableSession.objects.all()]
        }
        self.client.post(self.url, data=form_data)
        self.assertEqual(Event.objects.count(), 5)

        baker.make_recipe('booking.tue_session', _quantity=2)
        form_data.update(
            {'sessions': [session.id for session in TimetableSession.objects.all()]}
        )
        self.assertEqual(TimetableSession.objects.count(), 7)
        self.client.post(self.url, data=form_data)
        self.assertEqual(Event.objects.count(), 7)

    @patch('timetable.forms.timezone')
    def test_upload_timetable_with_duplicate_existing_classes(self, mock_tz):
        """
        add duplicates to context for warning display
        """
        self.client.login(username=self.superuser.username, password='test')
        mock_tz.now.return_value = datetime(
            2015, 6, 1, 0, 0, tzinfo=dt_timezone.utc
        )
        session = baker.make_recipe('booking.tue_session', name='test')
        # this session recipe has level 2 which will be incorporated into the class name

        # create date in Europe/London, convert to UTC
        localtz = pytz.timezone('Europe/London')
        local_ev_date = localtz.localize(datetime.combine(
            datetime(2015, 6, 2, 0, 0, tzinfo=dt_timezone.utc),
            session.start_time)
        )
        converted_ev_date = local_ev_date.astimezone(pytz.utc)

        # create duplicate existing classes for (tues) 2/6/15
        baker.make_recipe(
            'booking.future_PC', name='test (Level 2)',
            venue=session.venue,
            date=converted_ev_date,
            _quantity=2)
        self.assertEqual(Event.objects.count(), 2)
        form_data = {
            'start_date': 'Mon 01 Jun 2015',
            'end_date': 'Wed 03 Jun 2015',
            'sessions': [session.id]
        }

        resp = self.client.post(self.url, data=form_data)
        # no new classes created
        self.assertEqual(Event.objects.count(), 2)
        # duplicates in context for template warning
        self.assertEqual(len(resp.context['duplicate_classes']), 1)
        self.assertEqual(resp.context['duplicate_classes'][0]['count'], 2)
        self.assertEqual(
            resp.context['duplicate_classes'][0]['class'].name, 'test (Level 2)'
        )
        # existing in context for template warning (shows first of duplicates only)
        self.assertEqual(len(resp.context['existing_classes']), 1)
        self.assertEqual(resp.context['existing_classes'][0].name, 'test (Level 2)')
