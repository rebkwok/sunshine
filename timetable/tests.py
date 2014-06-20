from django.test import TestCase

import datetime

from django.utils import timezone

from timetable.models import Session, SessionType, Instructor, Venue, Event

from django.core.urlresolvers import reverse

def create_session(days, type=None):
    """
    Creates a session with session date the given number of
    `days` offset to now (negative for sessions in the past,
    positive for sessions in the future).
    """
    if type:
        test_venue = Venue.objects.create(venue="test venue")
        return Session.objects.create(session_date=timezone.now() + datetime.timedelta(days=days),
                               session_type=type,
                               venue=test_venue,
                               )
    else:
        test_session_type = SessionType.objects.create(name="test session type")
        test_venue = Venue.objects.create(venue="test venue")
        return Session.objects.create(session_date=timezone.now() + datetime.timedelta(days=days),
                                   session_type=test_session_type,
                                   venue=test_venue,
                                   )

def create_session_type(name, regular):
    """
    Creates a session_type with the given name and value of regular_session.
    """
    return SessionType.objects.create(name=name, regular_session=regular)


class TimetableTests(TestCase):

    def test_bookable_with_past_session(self):
        """
        bookable() should return False for sessions whose
        date is in the past even when spaces field is True
        """
        past_session = create_session(-1)
        self.assertEqual(past_session.bookable(), False)

    def test_bookable_with_future_session_no_spaces(self):
        """
        bookable() should return False for sessions whose
        date is in the future if spaces field is False (default is True)
        """
        future_session = create_session(1)
        future_session.spaces = False
        self.assertEqual(future_session.bookable(), False)

    def test_bookable_with_future_session_spaces(self):
        """
        bookable() should return True for sessions whose
        date is in the future if spaces field is True
        """
        future_session = create_session(1)
        self.assertEqual(future_session.bookable(), True)

    def test_get_weekday(self):
        """
        get_weekday should return the correct weekday as a string: 'Mon', 'Tues', 'Wed', 'Thurs', 'Fri', 'Sat', 'Sun'
        """
        tz = timezone.get_current_timezone()
        wed_date = datetime.datetime(2014, 06, 18, 12, 0, tzinfo=tz)
        wednesday_session = create_session(1)
        wednesday_session.session_date = wed_date
        self.assertEqual(wednesday_session.get_weekday(), 'Wed')



class TimetableViewTests(TestCase):

    def test_timetable_page(self):
        create_session(1)
        response = self.client.get(reverse('website:timetable'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue('timetable_items' in response.context)


    def test_timetable_view_with_no_sessions(self):
        """
        If no sessions exist, an appropriate message should be displayed.
        """
        response = self.client.get(reverse('website:timetable'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No classes are scheduled.")
        self.assertQuerysetEqual(response.context['timetable_items'], [])

    def test_timetable_view_with_past_session(self):
        """
        If only past sessions exist, an appropriate message should be displayed.
        """
        create_session(-1)
        response = self.client.get(reverse('website:timetable'))
        self.assertContains(response, "No classes are scheduled.", status_code=200)
        self.assertQuerysetEqual(response.context['timetable_items'], [])

    def test_timetable_view_with_future_session(self):
        """
        If future sessions exist, future sessions should be displayed.
        """
        create_session(4)
        response = self.client.get(reverse('website:timetable'))
        self.assertEqual([session.pk for session in response.context['timetable_items']], [1])

    def test_timetable_view_with_past_and_future_sessions(self):
        """
        If past and future sessions exist, only future sessions should be displayed.
        """
        create_session(2)
        create_session(-2)
        response = self.client.get(reverse('website:timetable'))
        self.assertEqual([session.pk for session in response.context['timetable_items']], [1])

    def test_timetable_session_type_list_for_navbar(self):
        """
        Navbar should display all session types where regular_session is True, even if there are no
        session objects with that session type
        """
        create_session_type("type1", True)
        create_session_type("type2", True)
        create_session_type("type3", False)
        response = self.client.get(reverse('website:timetable'))
        self.assertQuerysetEqual(response.context['session_types'], ['<SessionType: type1>', '<SessionType: type2>'])

    def test_timetable_session_type_list_for_sidebar_with_future_sessions(self):
        """
        Sidebar should display all session types that have a session with that session type.  If a session type exists
        but has no future scheduled sessions, the type will not display
        """
        type1 = create_session_type("type1", True)
        type2 =create_session_type("type2", False)
        type3 =create_session_type("type3", False)
        create_session(2, type1)
        create_session(4, type2)

        response = self.client.get(reverse('website:timetable'))
        self.assertQuerysetEqual(response.context['tt_session_types'], ['<SessionType: type1>', '<SessionType: type2>'])

    def test_timetable_session_type_list_for_sidebar_with_past_sessions(self):
        """
        Sidebar should display all session types that have a session with that session type.  If a session type exists
        but has no future scheduled sessions, the type will not display
        """
        type1 = create_session_type("type1", True) # only has a past session
        type2 =create_session_type("type2", False) # has a future session so will be displayed, even though not a regular session type
        type3 =create_session_type("type3", True) # no associated session
        create_session(-2, type1)
        create_session(4, type2)

        response = self.client.get(reverse('website:timetable'))
        self.assertQuerysetEqual(response.context['tt_session_types'], ['<SessionType: type2>'])

class WeeklyTableViewTests(TestCase):

    def test_weekly_table_session_type_list_for_navbar(self):
        """
        Navbar should display all session types where regular_session is True, even if there are no
        session objects with that session type
        """
        create_session_type("type1", True)
        create_session_type("type2", True)
        create_session_type("type3", False)
        response = self.client.get(reverse('website:this_week_table'))
        self.assertQuerysetEqual(response.context['session_types'], ['<SessionType: type1>', '<SessionType: type2>'])

    def test_weekly_table_session_type_list_for_sidebar_with_future_sessions(self):
        """
        Sidebar should display all session types that have a session with that session type.  If a session type exists
        but has no scheduled sessions beyond Monday of this week, the type will not display
        """

        now = timezone.now()
        mon_offset = 0 - now.weekday()

        type1 = create_session_type("type1", True)
        type2 =create_session_type("type2", False)
        type3 =create_session_type("type3", False)
        create_session(mon_offset, type1)
        create_session(4, type2)

        response = self.client.get(reverse('website:this_week_table'))
        self.assertQuerysetEqual(response.context['tt_session_types'], ['<SessionType: type1>', '<SessionType: type2>'])

    def test_weekly_table_session_type_list_for_sidebar_with_past_sessions(self):
        """
        Sidebar should display all session types that have a session with that session type.  If a session type exists
        but has no future scheduled sessions, the type will not display
        """
        now = timezone.now()
        mon_offset = 0 - now.weekday()
        
        type1 = create_session_type("type1", True) # only has a past session
        type2 =create_session_type("type2", False) # has a future session so will be displayed, even though not a regular session type
        type3 =create_session_type("type3", True) # no associated session
        create_session(mon_offset-2, type1)
        create_session(4, type2)

        response = self.client.get(reverse('website:this_week_table'))
        self.assertQuerysetEqual(response.context['tt_session_types'], ['<SessionType: type2>'])
