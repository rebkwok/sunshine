# -*- coding: utf-8 -*-
from model_mommy import mommy

from django.test import TestCase
from django.contrib.admin.sites import AdminSite
from django.core import management

from timetable.models import SessionType, TimetableSession, Instructor, \
    MembershipClassLevel, Venue
from website.models import AboutInfo

import website.admin as admin


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


class AdminTests(TestCase):

    def test_about_info_admin_display(self):
        info = mommy.make(AboutInfo)

        info_admin = admin.AboutInfoAdmin(AboutInfo, AdminSite())
        info_query = info_admin.get_queryset(None)[0]

        self.assertEqual(info_admin.get_id(info_query), info.id)
        self.assertEqual(
            info_admin.get_id.short_description, 'Section number'
        )
