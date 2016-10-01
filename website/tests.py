# -*- coding: utf-8 -*-
import os
from model_mommy import mommy

from django.test import TestCase, override_settings
from django.contrib.admin.sites import AdminSite
from django.core import management
from django.core.urlresolvers import reverse

from timetable.models import SessionType, TimetableSession, Instructor, \
    MembershipClassLevel, Venue
from website.models import AboutInfo

import website.admin as admin


TEMP_MEDIA_FOLDER = os.path.join(
            os.path.abspath(os.path.dirname(__file__)), 'website/testdata/'
        )


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


@override_settings(MEDIA_ROOT=TEMP_MEDIA_FOLDER)
class WebsitePagesTests(TestCase):

    def test_get_about_page(self):
        # with no about info
        resp = self.client.get(reverse('website:about'))
        self.assertEqual(resp.status_code, 200)

        mommy.make(
            AboutInfo, heading='About', subheading='Our subheading',
            content='Foo'
        )
        resp = self.client.get(reverse('website:about'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('<h1>About</h1>', str(resp.content))
        self.assertIn('<h3>Our subheading</h3>', str(resp.content))
        self.assertIn('<p>Foo</p>', str(resp.content))


    def test_get_classes_page(self):
        # with no info
        resp = self.client.get(reverse('website:classes'))
        self.assertEqual(resp.status_code, 200)

        # with info, no images
        session_type = mommy.make(
            SessionType, name="Polefit", info='About pole'
        )
        resp = self.client.get(reverse('website:classes'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('<h3>Polefit</h3>', str(resp.content))
        self.assertIn('<p>About pole</p>', str(resp.content))

        # with image
        session_type.photo = 'photo.jpg'
        session_type.save()
        resp = self.client.get(reverse('website:classes'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('<h3>Polefit</h3>', str(resp.content))
        self.assertIn('<p>About pole</p>', str(resp.content))
        self.assertIn("photo.jpg", str(resp.content))

    def test_get_parties_page(self):
        resp = self.client.get(reverse('website:parties'))
        self.assertEqual(resp.status_code, 200)

    def test_get_membership_page(self):
        resp = self.client.get(reverse('website:membership'))
        self.assertEqual(resp.status_code, 200)

    def test_get_venues_page(self):
        resp = self.client.get(reverse('website:venues'))
        self.assertEqual(resp.status_code, 200)

    def test_get_instructors_page(self):
        # with no info
        resp = self.client.get(reverse('website:instructors'))
        self.assertEqual(resp.status_code, 200)

        # with info
        instructor = mommy.make(Instructor, name='Kira', info="About Kira.")
        resp = self.client.get(reverse('website:instructors'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('<h3>Kira</h3>', str(resp.content))
        self.assertIn('<p>About Kira.</p>', str(resp.content))

        # with image
        instructor.photo = 'photo.jpg'
        instructor.save()
        resp = self.client.get(reverse('website:instructors'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('<h3>Kira</h3>', str(resp.content))
        self.assertIn('<p>About Kira.</p>', str(resp.content))
        self.assertIn('photo.jpg', str(resp.content))
