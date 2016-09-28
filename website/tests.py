# -*- coding: utf-8 -*-

from django.test import TestCase
from django.core import management

from timetable.models import SessionType, TimetableSession, Instructor, \
    MembershipClassLevel, Venue
from website.models import AboutInfo


class ManagementCommands(TestCase):

    def test_populatedb(self):

        self.assertFalse(SessionType.objects.exists())
        self.assertFalse(TimetableSession.objects.exists())
        self.assertFalse(Instructor.objects.exists())
        self.assertFalse(MembershipClassLevel.objects.exists())
        self.assertFalse(Venue.objects.exists())
        self.assertFalse(AboutInfo.objects.exists())

        management.call_command('populatedb')

        self.assertEqual(Instructor.objects.count(), 5)
        self.assertEqual(Venue.objects.count(), 5)
        self.assertEqual(SessionType.objects.count(), 7)
        self.assertEqual(MembershipClassLevel.objects.count(), 3)
        self.assertEqual(TimetableSession.objects.count(), 42)
        self.assertEqual(AboutInfo.objects.count(), 1)

        # rerunning doesn't create additional items
        management.call_command('populatedb')

        self.assertEqual(Instructor.objects.count(), 5)
        self.assertEqual(Venue.objects.count(), 5)
        self.assertEqual(SessionType.objects.count(), 7)
        self.assertEqual(MembershipClassLevel.objects.count(), 3)
        self.assertEqual(TimetableSession.objects.count(), 42)
        self.assertEqual(AboutInfo.objects.count(), 1)
