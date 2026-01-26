import pytest

from model_bakery import baker

from django.core import management
from django.test import TestCase

from ..models import SessionType, TimetableSession, Venue


pytestmark = pytest.mark.django_db


class ManagementCommands(TestCase):

    def test_populatedb(self):

        self.assertFalse(SessionType.objects.exists())
        self.assertFalse(TimetableSession.objects.exists())
        self.assertFalse(Venue.objects.exists())

        management.call_command('populatedb')

        self.assertEqual(Venue.objects.count(), 2)
        self.assertEqual(SessionType.objects.count(), 3)
        self.assertEqual(TimetableSession.objects.count(), 3)

        # rerunning doesn't create additional items
        management.call_command('populatedb')

        self.assertEqual(Venue.objects.count(), 2)
        self.assertEqual(SessionType.objects.count(), 3)
        self.assertEqual(TimetableSession.objects.count(), 3)
