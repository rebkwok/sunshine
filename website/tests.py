# -*- coding: utf-8 -*-
import os
from datetime import datetime, time, timedelta
from unittest.mock import patch
from model_mommy import mommy

from django.conf import settings
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.core import mail, management
from django.urls import reverse
from django.test import override_settings, TestCase
from django.utils import timezone

from timetable.models import SessionType, TimetableSession, Instructor, Venue
from website.forms import BookingRequestForm
from website.models import AboutInfo, Achievement, PastEvent

import website.admin as admin


TEMP_MEDIA_FOLDER = os.path.join(
            os.path.abspath(os.path.dirname(__file__)), 'website/testdata/'
        )


class ManagementCommands(TestCase):

    def test_populatedb(self):

        self.assertFalse(SessionType.objects.exists())
        self.assertFalse(TimetableSession.objects.exists())
        self.assertFalse(Instructor.objects.exists())
        self.assertFalse(Venue.objects.exists())
        self.assertFalse(AboutInfo.objects.exists())

        management.call_command('populatedb')

        self.assertEqual(Instructor.objects.count(), 5)
        self.assertEqual(Venue.objects.count(), 5)
        self.assertEqual(SessionType.objects.count(), 7)
        self.assertEqual(TimetableSession.objects.count(), 42)
        self.assertEqual(AboutInfo.objects.count(), 1)

        # rerunning doesn't create additional items
        management.call_command('populatedb')

        self.assertEqual(Instructor.objects.count(), 5)
        self.assertEqual(Venue.objects.count(), 5)
        self.assertEqual(SessionType.objects.count(), 7)
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


class ModelTests(TestCase):

    def test_about_info_str(self):
        about = mommy.make(
            AboutInfo, heading='Foo', content='Foo'
        )
        self.assertEqual(
            str(about), 'About page section {}'.format(about.id)
        )

    def test_past_event_str(self):
        past = mommy.make(PastEvent, name="past event")
        self.assertEqual(str(past), 'past event')

    def test_achievement_str(self):
        past = mommy.make(PastEvent, name="past event")
        achievement = mommy.make(
            Achievement, event=past, category='Pro')
        self.assertEqual(str(achievement), 'past event, Pro')


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


class ContactFormTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.url = reverse('website:contact_form')
        cls.user = User.objects.create(
            username='test', email='test@test.com', password='test'
        )

    def test_get_contact_form(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)

        # no data on session
        self.assertEqual(
            resp.context['form'].initial['subject'], 'General Enquiry'
        )
        self.assertEqual(
            resp.context['form'].initial['first_name'], ''
        )
        self.assertEqual(
            resp.context['form'].initial['last_name'], ''
        )
        self.assertEqual(
            resp.context['form'].initial['email_address'], ''
        )

        sess = self.client.session
        sess['first_name'] = 'Donald'
        sess['last_name'] = "Duck"
        sess['email_address'] = 'dd@test.com'
        sess.save()

        resp = self.client.get(
            self.url, HTTP_REFERER='http://test.com/membership/'
        )

        # data on session
        self.assertEqual(
            resp.context['form'].initial['subject'], 'Membership Enquiry'
        )
        self.assertEqual(
            resp.context['form'].initial['first_name'], 'Donald'
        )
        self.assertEqual(
            resp.context['form'].initial['last_name'], 'Duck'
        )
        self.assertEqual(
            resp.context['form'].initial['email_address'], 'dd@test.com'
        )

    def test_get_contact_page(self):
        resp = self.client.get(reverse('website:contact'))
        self.assertEqual(resp.status_code, 200)

        # no data on session
        self.assertEqual(
            resp.context['form'].initial['subject'], 'General Enquiry'
        )
        self.assertEqual(
            resp.context['form'].initial['first_name'], ''
        )
        self.assertEqual(
            resp.context['form'].initial['last_name'], ''
        )
        self.assertEqual(
            resp.context['form'].initial['email_address'], ''
        )

    def test_send_contact_form(self):
        data = {
            'subject': 'General Enquiry',
            'first_name': 'Donald',
            'last_name': 'Duck',
            'email_address': 'dd@test.com',
            'message': 'Test message',
            'cc': True
        }

        resp = self.client.post(self.url, data)
        self.assertEqual(resp.status_code, 302)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [settings.DEFAULT_STUDIO_EMAIL])
        self.assertEqual(mail.outbox[0].cc, ['dd@test.com'])

    def test_send_contact_form_with_errors(self):
        data = {
            'subject': 'General Enquiry',
            'first_name': 'Donald',
            'last_name': 'Duck',
            'email_address': 'dd@test.com',
            'message': '',
            'cc': True
        }

        resp = self.client.post(self.url, data)
        self.assertFalse(resp.context['form'].is_valid())
        self.assertEqual(
            resp.context['form'].errors,
            {'message': ['This field is required.']}
        )
        self.assertEqual(len(mail.outbox), 0)

    @patch('booking.email_helpers.EmailMultiAlternatives.send')
    def test_send_contact_form_with_email_errors(self, mock_send_emails):
        mock_send_emails.side_effect = Exception('Error sending mail')
        data = {
            'subject': 'General Enquiry',
            'first_name': 'Donald',
            'last_name': 'Duck',
            'email_address': 'dd@test.com',
            'message': 'Msg',
            'cc': True
        }

        resp = self.client.post(self.url, data, follow=True)

        self.assertEqual(len(mail.outbox), 0)
        self.assertIn(
            "A problem occurred while submitting your request.  Tech support "
            "has been notified.",
            str(resp.content)
        )


class BookingRequestTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.ttsession = mommy.make(
            TimetableSession, name='Polefit', session_day='01MO',
            start_time=time(18, 0), venue__abbreviation='Inverkeithing'
        )
        cls.url = reverse('website:booking_request', args=[cls.ttsession.id])
        cls.user = User.objects.create(
            username='test', email='test@test.com', password='test'
        )

    def test_get_booking_request_form(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)

        # no data on session
        self.assertEqual(
            resp.context['form'].initial['first_name'], ''
        )
        self.assertEqual(
            resp.context['form'].initial['last_name'], ''
        )
        self.assertEqual(
            resp.context['form'].initial['email_address'], ''
        )

        sess = self.client.session
        sess['first_name'] = 'Donald'
        sess['last_name'] = "Duck"
        sess['email_address'] = 'dd@test.com'
        sess.save()

        resp = self.client.get(self.url)

        # data on session
        self.assertEqual(
            resp.context['form'].initial['first_name'], 'Donald'
        )
        self.assertEqual(
            resp.context['form'].initial['last_name'], 'Duck'
        )
        self.assertEqual(
            resp.context['form'].initial['email_address'], 'dd@test.com'
        )

    @patch('website.forms.timezone')
    def test_send_booking_request(self, mock_tz):
        mock_now = datetime(
            2016, 10, 3, 15, 0, tzinfo=timezone.utc
        )
        mock_tz.now.return_value = mock_now

        # Monday = 0
        days_ahead = 0 - mock_now.weekday()
        if days_ahead < 0:  # Target day already happened this week
            days_ahead += 7
        next_date = mock_now + timedelta(days_ahead)

        data = {
            'first_name': 'Donald',
            'last_name': 'Duck',
            'email_address': 'dd@test.com',
            'additional_msg': 'Test message',
            'cc': True,
            'date': next_date.strftime('%a %d %b %y')
        }

        resp = self.client.post(self.url, data)
        self.assertEqual(resp.status_code, 302)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [settings.DEFAULT_STUDIO_EMAIL])
        self.assertEqual(mail.outbox[0].cc, ['dd@test.com'])

        # subject comes from timetable session info
        self.assertEqual(
            mail.outbox[0].subject,
            '{} Booking request for Polefit (All levels), Inverkeithing, '
            'Monday 18:00'.format(settings.ACCOUNT_EMAIL_SUBJECT_PREFIX)
        )

    @patch('website.forms.timezone')
    def test_post_booking_request_with_errors(self, mock_tz):
        mock_now = datetime(
            2016, 10, 3, 15, 0, tzinfo=timezone.utc
        )
        mock_tz.now.return_value = mock_now

        # Monday = 0
        days_ahead = 0 - mock_now.weekday()
        if days_ahead < 0:  # Target day already happened this week
            days_ahead += 7
        next_date = mock_now + timedelta(days_ahead)

        data = {
            'first_name': 'Donald',
            'last_name': '',
            'email_address': 'dd@test.com',
            'additional_msg': '',
            'cc': True,
            'date': next_date.strftime('%a %d %b %y')
        }

        resp = self.client.post(self.url, data)

        self.assertFalse(resp.context['form'].is_valid())
        self.assertEqual(
            resp.context['form'].errors,
            {'last_name': ['This field is required.']}
        )

        self.assertEqual(len(mail.outbox), 0)

    @patch('booking.email_helpers.EmailMultiAlternatives.send')
    @patch('website.forms.timezone')
    def test_send_booking_request_with_email_errors(self, mock_tz, mock_send):
        mock_now = datetime(
            2016, 10, 3, 15, 0, tzinfo=timezone.utc
        )
        mock_tz.now.return_value = mock_now

        # Monday = 0
        days_ahead = 0 - mock_now.weekday()
        if days_ahead < 0:  # Target day already happened this week
            days_ahead += 7
        next_date = mock_now + timedelta(days_ahead)

        mock_send.side_effect = Exception('Error sending mail')

        data = {
            'first_name': 'Donald',
            'last_name': 'Duck',
            'email_address': 'dd@test.com',
            'additional_msg': 'Test message',
            'cc': True,
            'date': next_date.strftime('%a %d %b %y')
        }

        resp = self.client.post(self.url, data, follow=True)

        self.assertEqual(len(mail.outbox), 0)
        self.assertIn(
            "A problem occurred while submitting your request.  Tech support "
            "has been notified.",
            str(resp.content)
        )

    @patch('website.forms.timezone')
    def test_date_options(self, mock_tz):
        """
        Date options in request form show the next 4 weeks plus regular
        booking option"""
        # set now to be same weekday as self.ttsession
        mock_tz.now.return_value = datetime(
            2016, 10, 3, 15, 0, tzinfo=timezone.utc
        )

        # date choices include today
        form = BookingRequestForm(session=self.ttsession)
        self.assertEqual(
            form.fields['date'].choices,
            [
                ('Mon 03 Oct 16', 'Mon 03 Oct 16'),
                ('Mon 10 Oct 16', 'Mon 10 Oct 16'),
                ('Mon 17 Oct 16', 'Mon 17 Oct 16'),
                ('Mon 24 Oct 16', 'Mon 24 Oct 16'),
                ('Regular weekly booking', 'Regular weekly booking')
            ]
        )

        # set now to be later than self.ttsession
        mock_tz.now.return_value = datetime(
            2016, 10, 5, 15, 0, tzinfo=timezone.utc
        )
        # date choices for next 4 weeks
        form = BookingRequestForm(session=self.ttsession)
        self.assertEqual(
            form.fields['date'].choices,
            [
                ('Mon 10 Oct 16', 'Mon 10 Oct 16'),
                ('Mon 17 Oct 16', 'Mon 17 Oct 16'),
                ('Mon 24 Oct 16', 'Mon 24 Oct 16'),
                ('Mon 31 Oct 16', 'Mon 31 Oct 16'),
                ('Regular weekly booking', 'Regular weekly booking')
            ]
        )

        # set now to be same day but after class started
        mock_tz.now.return_value = datetime(
            2016, 10, 3, 18, 10, tzinfo=timezone.utc
        )
        # date choices for next 4 weeks
        form = BookingRequestForm(session=self.ttsession)
        self.assertEqual(
            form.fields['date'].choices,
            [
                ('Mon 10 Oct 16', 'Mon 10 Oct 16'),
                ('Mon 17 Oct 16', 'Mon 17 Oct 16'),
                ('Mon 24 Oct 16', 'Mon 24 Oct 16'),
                ('Mon 31 Oct 16', 'Mon 31 Oct 16'),
                ('Regular weekly booking', 'Regular weekly booking')
            ]
        )