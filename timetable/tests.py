from model_mommy import mommy

from django.test import TestCase

from timetable.models import TimetableSession, SessionType, Instructor, Venue
from django.core.urlresolvers import reverse


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

