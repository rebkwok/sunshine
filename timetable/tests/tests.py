from model_bakery import baker

from django.core import management
from django.test import TestCase

from .models import SessionType, TimetableSession, Venue



class ModelTests(TestCase):

    def test_session_type_str(self):
        session_type = baker.make(SessionType, name="Pole")
        self.assertEqual(str(session_type), "Pole")

    def test_venue_str(self):
        venue = baker.make(
            Venue, venue="Sunshine Studio",
            address="1 Street",
            abbreviation="Sunshine"
        )
        self.assertEqual(str(venue), "Sunshine Studio")


class ManagementCommands(TestCase):

    def test_populatedb(self):

        self.assertFalse(SessionType.objects.exists())
        self.assertFalse(TimetableSession.objects.exists())
        self.assertFalse(Venue.objects.exists())

        management.call_command('populatedb')

        self.assertEqual(Venue.objects.count(), 5)
        self.assertEqual(SessionType.objects.count(), 7)
        self.assertEqual(TimetableSession.objects.count(), 3)

        # rerunning doesn't create additional items
        management.call_command('populatedb')

        self.assertEqual(Venue.objects.count(), 5)
        self.assertEqual(SessionType.objects.count(), 7)
        self.assertEqual(TimetableSession.objects.count(), 3)
