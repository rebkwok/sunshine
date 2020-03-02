# -*- coding: utf-8 -*-
from datetime import datetime
from unittest.mock import patch
from model_bakery import baker

from django.conf import settings
from django.core import mail
from django.urls import reverse
from django.test import override_settings, TestCase
from django.utils import timezone

from accounts.tests import make_data_privacy_agreement

from ..models import Event, Booking, WaitingListUser
from .helpers import TestSetupMixin


class BookingToggleAjaxCreateViewTests(TestSetupMixin, TestCase):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.event = baker.make_recipe(
            'booking.future_PC', email_studio_when_booked=True, cost=5, max_participants=3
        )
        cls.url = reverse('booking:toggle_booking', args=[cls.event.id])

    def setUp(self):
        super().setUp()
        make_data_privacy_agreement(self.user)

    def test_create_booking(self):
        """
        Test creating a booking
        """
        self.assertEqual(Booking.objects.all().count(), 0)
        self.client.login(username=self.user.username, password='test')
        resp = self.client.post(self.url)
        self.assertEqual(Booking.objects.all().count(), 1)
        self.assertEqual(resp.context['alert_message']['message'], 'Booked.')
        self.assertFalse(Booking.objects.first().paid)

        # email to student and studio
        self.assertEqual(len(mail.outbox), 2)

    def test_create_booking_sends_email_to_studio_if_set(self):
        """
        Test creating a booking send email to user and studio if flag sent on
        event
        """
        event = baker.make_recipe(
            'booking.future_EV', cost=5, max_participants=3,
            email_studio_when_booked=False
        )
        url = reverse('booking:toggle_booking', args=[event.id])
        self.assertEqual(Booking.objects.all().count(), 0)
        self.client.login(username=self.user.username, password='test')
        self.client.post(url)
        self.assertEqual(Booking.objects.all().count(), 1)
        # email to student only
        self.assertEqual(len(mail.outbox), 1)

    def test_cannot_book_for_full_event(self):
        """
        Test trying create booking for a full event returns 400
        """
        users = baker.make_recipe('booking.user', _quantity=3)
        for user in users:
            baker.make_recipe('booking.booking', event=self.event, user=user)
        # check event is full; we need to get the event again as spaces_left is
        # cached property
        event = Event.objects.get(id=self.event.id)
        self.assertEqual(event.spaces_left, 0)

        self.client.login(username=self.user.username, password='test')
        # try to book for event
        resp = self.client.post(self.url)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.content.decode('utf-8'), 'Sorry, this class is now full')

    def test_cannot_book_for_cancelled_event(self):
        """cannot create booking for a full event
        """
        event = baker.make_recipe('booking.future_EV', max_participants=3, cancelled=True, cost=5)
        url = reverse('booking:toggle_booking', args=[event.id])

        self.client.login(username=self.user.username, password='test')
        # try to book for event
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.content.decode('utf-8'), 'Sorry, this workshop has been cancelled')

    def test_cancelled_booking_can_be_rebooked(self):
        """
        Test can load create booking page with a cancelled booking
        """
        booking = baker.make_recipe(
            'booking.booking', event=self.event, user=self.user, status='CANCELLED'
        )

        self.client.login(username=self.user.username, password='test')
        # try to book again
        resp = self.client.post(self.url)

        booking.refresh_from_db()
        self.assertEqual(booking.status, 'OPEN')
        self.assertIsNotNone(booking.date_rebooked)

        self.assertEqual(
            resp.context['alert_message']['message'],
            'Booked.'
        )

    def test_rebook_no_show_booking(self):
        """
        Test can rebook a booking marked as no_show
        """
        pclass = baker.make_recipe(
            'booking.future_PC', allow_booking_cancellation=False, cost=10
        )
        url = reverse('booking:toggle_booking', args=[pclass.id])

        # book for non-refundable event and mark as no_show
        booking = baker.make_recipe(
            'booking.booking', user=self.user, event=pclass, paid=True,
            no_show=True
        )
        self.assertIsNone(booking.date_rebooked)

        # try to book again
        self.client.login(username=self.user.username, password='test')
        resp = self.client.post(url)
        booking.refresh_from_db()
        self.assertEqual('OPEN', booking.status)
        self.assertFalse(booking.no_show)
        self.assertIsNotNone(booking.date_rebooked)
        self.assertEqual(
            resp.context['alert_message']['message'], 'Booked.'
        )

        # emails sent to student and studio
        self.assertEqual(len(mail.outbox), 2)
        email = mail.outbox[0]
        self.assertEqual(email.to, ['test@test.com'])

    def test_create_booking_user_on_waiting_list(self):
        """
        Test creating a booking for a user on the waiting list deletes waiting list
        """
        baker.make(WaitingListUser, event=self.event, user=self.user)
        baker.make(WaitingListUser, event=self.event)
        baker.make(WaitingListUser, user=self.user)
        self.assertEqual(Booking.objects.all().count(), 0)
        self.client.login(username=self.user.username, password='test')

        self.client.post(self.url)
        self.assertEqual(Booking.objects.all().count(), 1)
        # the waiting list user for this user and event only has been deleted
        self.assertEqual(WaitingListUser.objects.all().count(), 2)
        self.assertFalse(WaitingListUser.objects.filter(user=self.user, event=self.event).exists())

        # email to student and studio
        self.assertEqual(len(mail.outbox), 2)

    def test_cancel_booking(self):
        """
        Toggle booking to cancelled
        """
        booking = baker.make_recipe('booking.booking', user=self.user, event=self.event)
        self.client.login(username=self.user.username, password='test')
        resp = self.client.post(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp.context['alert_message']['message'], 'Cancelled.'
        )
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'CANCELLED')

    @patch('booking.models.timezone.now')
    def test_cancel_booking_within_cancellation_period(self, mock_now):
        """
        Toggle booking to no-show
        """
        mock_now.return_value = datetime(2018, 1, 1, 9, tzinfo=timezone.utc)
        event = baker.make_recipe('booking.future_PC', date=datetime(2018, 1, 1, 10, tzinfo=timezone.utc))
        url = reverse('booking:toggle_booking', args=[event.id])

        booking = baker.make_recipe(
            'booking.booking', user=self.user, event=event,
            date_booked=datetime(2018, 1, 1, 8, 44, tzinfo=timezone.utc)  # booked > 15 mins ago
        )
        self.client.login(username=self.user.username, password='test')
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp.context['alert_message']['message'], 'Cancelled.'
        )
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'OPEN')
        self.assertTrue(booking.no_show)

    @patch('booking.models.timezone.now')
    def test_cancel_booking_within_5_mins_during_cancellation_period(self, mock_now):
        """
        Cancelling within 5 mins allows proper cancelling
        """
        mock_now.return_value = datetime(2018, 1, 1, 9, tzinfo=timezone.utc)
        event = baker.make_recipe('booking.future_PC', date=datetime(2018, 1, 1, 10, tzinfo=timezone.utc))
        url = reverse('booking:toggle_booking', args=[event.id])
        self.client.login(username=self.user.username, password='test')

        booking = baker.make_recipe(
            'booking.booking', user=self.user, event=event,
            date_booked=datetime(2018, 1, 1, 8, 56, tzinfo=timezone.utc)
        )

        resp = self.client.post(url)
        booking.refresh_from_db()
        self.assertEqual(resp.context['alert_message']['message'], 'Cancelled.')
        self.assertEqual(booking.status, 'CANCELLED')
        self.assertFalse(booking.no_show)

    @patch('booking.models.timezone.now')
    def test_cancel_rebooking_within_5_mins_during_cancellation_period(self, mock_now):
        """
        Cancelling within 5 mins of rebooking allows proper cancelling
        """
        mock_now.return_value = datetime(2018, 1, 1, 9, tzinfo=timezone.utc)
        event = baker.make_recipe('booking.future_PC', date=datetime(2018, 1, 1, 10, tzinfo=timezone.utc))
        url = reverse('booking:toggle_booking', args=[event.id])
        self.client.login(username=self.user.username, password='test')

        booking = baker.make_recipe(
            'booking.booking', user=self.user, event=event,
            date_booked=datetime(2018, 1, 1, 5, 0, tzinfo=timezone.utc),
            date_rebooked=datetime(2018, 1, 1, 8, 56, tzinfo=timezone.utc)
        )
        resp = self.client.post(url)
        booking.refresh_from_db()
        self.assertEqual(resp.context['alert_message']['message'], 'Cancelled.')
        self.assertEqual(booking.status, 'CANCELLED')
        self.assertFalse(booking.no_show)

    def test_cancel_full_booking_emails_waiting_list(self):
        """
        Toggle booking to cancelled
        """
        booking = baker.make_recipe('booking.booking', user=self.user, event=self.event)
        baker.make_recipe('booking.booking', event=self.event, _quantity=2)
        for i in range(3):
            baker.make(WaitingListUser, event=self.event, user__email='test{}@test.test'.format(i))

        event = Event.objects.get(id=self.event.id)
        self.assertFalse(event.spaces_left)

        self.client.login(username=self.user.username, password='test')
        resp = self.client.post(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp.context['alert_message']['message'], 'Cancelled.'
        )
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'CANCELLED')
        self.assertEqual(len(mail.outbox), 3)  # email to user, studio and 1 to all 3 waiting list users
        wl_email = mail.outbox[2]
        self.assertEqual(len(wl_email.bcc), 3)

    @override_settings(AUTO_BOOK_EMAILS=['test1@test.test'])
    def test_cancel_full_booking_emails_auto_book_user_on_waiting_list(self):
        # if autobook user is on waiting list, create booking, email user, DO NOT email rest of waiting list
        baker.make_recipe('booking.booking', user=self.user, event=self.event)
        baker.make_recipe('booking.booking', event=self.event, _quantity=2)
        for i in range(3):
            baker.make(WaitingListUser, event=self.event, user__email='test{}@test.test'.format(i))

        self.assertFalse(self.event.spaces_left)
        self.assertFalse('test1@test.test' in self.event.bookings.filter(status='OPEN', no_show=False)
                         .values_list('user__email', flat=True))

        # cancel booking
        self.client.login(username=self.user.username, password='test')
        self.client.post(self.url)

        self.event.refresh_from_db()
        # still no spaces left because autobook user has been booked
        self.assertFalse(self.event.spaces_left)
        self.assertTrue('test1@test.test' in self.event.bookings.filter(status='OPEN', no_show=False)
                        .values_list('user__email', flat=True))
        self.assertFalse(WaitingListUser.objects.filter(user__email='test1@test.test').exists())

        # email to user, studio and 1 to autobook user. No waiting list emails
        self.assertEqual(len(mail.outbox), 3)
        self.assertEqual(
            [[self.user.email], [settings.DEFAULT_STUDIO_EMAIL], ['test1@test.test']],
            [mail.to for mail in mail.outbox]
        )
        self.assertIn('You have been booked into', mail.outbox[2].subject)

    @override_settings(AUTO_BOOK_EMAILS=['test1@test.test', 'test0@test.test'])
    def test_cancel_full_booking_emails_auto_book_user_on_waiting_list_multiple_users(self):
        # if autobook user is on waiting list, create booking for first autobook user, email user,
        # DO NOT email rest of waiting list
        # if autobook user is on waiting list, create booking, email user, DO NOT email rest of waiting list
        baker.make_recipe('booking.booking', user=self.user, event=self.event)
        baker.make_recipe('booking.booking', event=self.event, _quantity=2)
        for i in range(3):
            baker.make(WaitingListUser, event=self.event, user__email='test{}@test.test'.format(i))

        self.assertFalse(self.event.spaces_left)
        self.assertFalse('test1@test.test' in self.event.bookings.filter(status='OPEN', no_show=False)
                         .values_list('user__email', flat=True))

        # cancel booking
        self.client.login(username=self.user.username, password='test')
        self.client.post(self.url)

        self.event.refresh_from_db()
        # still no spaces left because autobook user has been booked
        self.assertFalse(self.event.spaces_left)
        # Only first autobook user booked
        open_booking_emails = self.event.bookings.filter(status='OPEN', no_show=False).values_list('user__email', flat=True)
        self.assertTrue('test1@test.test' in open_booking_emails)
        self.assertFalse(WaitingListUser.objects.filter(user__email='test1@test.test').exists())
        self.assertFalse('test0@test.test' in open_booking_emails)
        self.assertTrue(WaitingListUser.objects.filter(user__email='test0@test.test').exists())

        # email to user, studio and 1 to autobook user. No waiting list emails
        self.assertEqual(len(mail.outbox), 3)
        self.assertEqual(
            [[self.user.email], [settings.DEFAULT_STUDIO_EMAIL], ['test1@test.test']],
            [mail.to for mail in mail.outbox]
        )
        self.assertIn('You have been booked into', mail.outbox[2].subject)

    @override_settings(AUTO_BOOK_EMAILS=['test1@test.test'])
    def test_cancel_full_booking_emails_auto_book_user_on_waiting_list_previously_cancelled(self):
        # change existing booking to open, email user, DO NOT email rest of waiting list
        baker.make_recipe('booking.booking', user=self.user, event=self.event)
        cancelled_user = baker.make_recipe('booking.user', email='test1@test.test')
        booking = baker.make_recipe(
            'booking.booking', user=cancelled_user, event=self.event, status='CANCELLED'
        )
        self.assertIsNone(booking.date_rebooked)
        baker.make_recipe('booking.booking', event=self.event, _quantity=2)
        baker.make(WaitingListUser, event=self.event, user=cancelled_user)
        for i in range(2, 4):
            baker.make(WaitingListUser, event=self.event, user__email='test{}@test.test'.format(i))

        self.assertFalse(self.event.spaces_left)
        self.assertFalse('test1@test.test' in self.event.bookings.filter(status='OPEN', no_show=False)
                         .values_list('user__email', flat=True))

        # cancel booking
        self.client.login(username=self.user.username, password='test')
        self.client.post(self.url)

        self.event.refresh_from_db()
        # still no spaces left because autobook user has been booked
        self.assertFalse(self.event.spaces_left)
        # Only first autobook user booked
        open_booking_emails = self.event.bookings.filter(status='OPEN', no_show=False).values_list('user__email', flat=True)
        self.assertTrue('test1@test.test' in open_booking_emails)
        self.assertFalse(WaitingListUser.objects.filter(user__email='test1@test.test').exists())
        # booking has been reopened
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'OPEN')
        self.assertIsNotNone(booking.date_rebooked)

        # email to user, studio and 1 to autobook user. No waiting list emails
        self.assertEqual(len(mail.outbox), 3)
        self.assertEqual(
            [[self.user.email], [settings.DEFAULT_STUDIO_EMAIL], ['test1@test.test']],
            [mail.to for mail in mail.outbox]
        )
        self.assertIn('You have been booked into', mail.outbox[2].subject)

    @override_settings(AUTO_BOOK_EMAILS=['test1@test.test'])
    def test_cancel_full_booking_emails_auto_book_user_on_waiting_list_previously_no_show(self):
        # change existing booking to open/not no_show, email user, DO NOT email rest of waiting list
        baker.make_recipe('booking.booking', user=self.user, event=self.event)
        no_show_user = baker.make_recipe('booking.user', email='test1@test.test')
        booking = baker.make_recipe(
            'booking.booking', user=no_show_user, event=self.event, status='OPEN', no_show=True
        )
        self.assertIsNone(booking.date_rebooked)
        baker.make_recipe('booking.booking', event=self.event, _quantity=2)
        baker.make(WaitingListUser, event=self.event, user=no_show_user)
        for i in range(2, 4):
            baker.make(WaitingListUser, event=self.event, user__email='test{}@test.test'.format(i))

        self.assertFalse(self.event.spaces_left)
        self.assertFalse('test1@test.test' in self.event.bookings.filter(status='OPEN', no_show=False)
                         .values_list('user__email', flat=True))

        # cancel booking
        self.client.login(username=self.user.username, password='test')
        self.client.post(self.url)

        self.event.refresh_from_db()
        # still no spaces left because autobook user has been booked
        self.assertFalse(self.event.spaces_left)
        # Only first autobook user booked
        open_booking_emails = self.event.bookings.filter(status='OPEN', no_show=False).values_list('user__email', flat=True)
        self.assertTrue('test1@test.test' in open_booking_emails)
        self.assertFalse(WaitingListUser.objects.filter(user__email='test1@test.test').exists())
        # booking has been reopened
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'OPEN')
        self.assertIsNotNone(booking.date_rebooked)

        # email to user, studio and 1 to autobook user. No waiting list emails
        self.assertEqual(len(mail.outbox), 3)
        self.assertEqual(
            [[self.user.email], [settings.DEFAULT_STUDIO_EMAIL], ['test1@test.test']],
            [mail.to for mail in mail.outbox]
        )
        self.assertIn('You have been booked into', mail.outbox[2].subject)

    @override_settings(AUTO_BOOK_EMAILS=['test1@test.test'])
    def test_cancel_full_booking_emails_auto_book_user_on_waiting_list_already_booked(self):
        # leave existing booking as is, do not email autobook user, email rest of waiting list
        baker.make_recipe('booking.booking', user=self.user, event=self.event)
        open_user = baker.make_recipe('booking.user', email='test1@test.test')
        baker.make_recipe(
            'booking.booking', user=open_user, event=self.event, status='OPEN'
        )
        baker.make_recipe('booking.booking', event=self.event, _quantity=1)
        baker.make(WaitingListUser, event=self.event, user=open_user)
        for i in range(2, 4):
            baker.make(WaitingListUser, event=self.event, user__email='test{}@test.test'.format(i))

        self.assertFalse(self.event.spaces_left)
        self.assertTrue('test1@test.test' in self.event.bookings.filter(status='OPEN', no_show=False)
                         .values_list('user__email', flat=True))

        # cancel booking
        self.client.login(username=self.user.username, password='test')
        self.client.post(self.url)

        self.event.refresh_from_db()
        # a space left because autobook user was already booked
        self.assertEqual(self.event.spaces_left, 1)

        open_booking_emails = self.event.bookings.filter(status='OPEN', no_show=False).values_list('user__email', flat=True)
        self.assertTrue('test1@test.test' in open_booking_emails)
        # user removed from waiting list
        self.assertFalse(WaitingListUser.objects.filter(user__email='test1@test.test').exists())

        # email to user, studio and 1 to all waiting list emails
        self.assertEqual(len(mail.outbox), 3)
        self.assertEqual(
            [[self.user.email], [settings.DEFAULT_STUDIO_EMAIL], []],
            [mail.to for mail in mail.outbox]
        )
        self.assertIn('space now available', mail.outbox[2].subject)
        self.assertEqual(mail.outbox[2].bcc, ['test2@test.test', 'test3@test.test'])

    @override_settings(AUTO_BOOK_EMAILS=['test1@test.test', 'test2@test.test'])
    def test_cancel_full_booking_emails_auto_book_user_on_waiting_list_already_booked_multiple_users(self):
        # First autobook user of multiple is already booked
        # Leave existing booking as is, do not email first user
        # Create second user's booking and email, DO NOT email rest of waiting list
        baker.make_recipe('booking.booking', user=self.user, event=self.event)
        open_user = baker.make_recipe('booking.user', email='test1@test.test')
        booking = baker.make_recipe(
            'booking.booking', user=open_user, event=self.event, status='OPEN'
        )
        baker.make_recipe('booking.booking', event=self.event, _quantity=1)
        for i in range(2, 4):
            baker.make(WaitingListUser, event=self.event, user__email='test{}@test.test'.format(i))

        self.assertFalse(self.event.spaces_left)
        self.assertTrue('test1@test.test' in self.event.bookings.filter(status='OPEN', no_show=False)
                         .values_list('user__email', flat=True))

        # cancel booking
        self.client.login(username=self.user.username, password='test')
        self.client.post(self.url)

        self.event.refresh_from_db()
        # no space left because 2nd autobook user booked
        self.assertFalse(self.event.spaces_left)

        open_booking_emails = self.event.bookings.filter(status='OPEN', no_show=False).values_list('user__email', flat=True)
        self.assertTrue('test1@test.test' in open_booking_emails)
        self.assertTrue('test2@test.test' in open_booking_emails)
        # 2nd user removed from waiting list
        self.assertFalse(WaitingListUser.objects.filter(user__email='test2@test.test').exists())

        # email to cancelled user, studio and 2nd autobook user
        self.assertEqual(len(mail.outbox), 3)
        self.assertEqual(
            [[self.user.email], [settings.DEFAULT_STUDIO_EMAIL], ['test2@test.test']],
            [mail.to for mail in mail.outbox]
        )

    @override_settings(AUTO_BOOK_EMAILS=['test1@test.test'])
    def test_cancel_full_booking_emails_auto_book_user_not_on_waiting_list(self):
        # Email waiting list as normal
        # leave existing booking as is, do not email autobook user, email rest of waiting list
        baker.make_recipe('booking.booking', user=self.user, event=self.event)
        baker.make_recipe(
            'booking.booking', user__email='test1@test.test', event=self.event, status='OPEN'
        )
        baker.make_recipe('booking.booking', event=self.event, _quantity=1)

        for i in range(2, 4):
            baker.make(WaitingListUser, event=self.event, user__email='test{}@test.test'.format(i))

        # cancel booking
        self.client.login(username=self.user.username, password='test')
        self.client.post(self.url)

        self.event.refresh_from_db()
        # a space left because autobook user was already booked
        self.assertEqual(self.event.spaces_left, 1)

        # autobook user still booked and not on waiting list
        open_booking_emails = self.event.bookings.filter(status='OPEN', no_show=False).values_list('user__email', flat=True)
        self.assertTrue('test1@test.test' in open_booking_emails)
        # user removed from waiting list
        self.assertFalse(WaitingListUser.objects.filter(user__email='test1@test.test').exists())

        # email to user, studio and 1 to all waiting list emails
        self.assertEqual(len(mail.outbox), 3)
        self.assertEqual(
            [[self.user.email], [settings.DEFAULT_STUDIO_EMAIL], []],
            [mail.to for mail in mail.outbox]
        )
        self.assertIn('space now available', mail.outbox[2].subject)
        self.assertEqual(mail.outbox[2].bcc, ['test2@test.test', 'test3@test.test'])

    def test_error_if_outstanding_fees(self):
        baker.make_recipe('booking.booking', user=self.user, cancellation_fee_incurred=True)
        self.client.login(username=self.user.username, password='test')
        resp = self.client.post(self.url)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.content.decode('utf-8'), "Action forbidden until outstanding cancellation fees have been resolved")


class AjaxTests(TestSetupMixin, TestCase):

    def setUp(self):
        super().setUp()
        self.event = baker.make_recipe('booking.future_PC', max_participants=3)
        self.client.login(username=self.user.username, password='test')

    def test_update_bookings_count_spaces(self):
        url = reverse('booking:update_booking_count', args=[self.event.id])
        resp = self.client.get(url)
        self.assertEqual(resp.json(), {'booking_count': '3/3', 'full': False, 'booked': False})

    def test_update_bookings_count_full(self):
        url = reverse('booking:update_booking_count', args=[self.event.id])
        baker.make_recipe('booking.booking', event=self.event, _quantity=3)
        resp = self.client.get(url)
        self.assertEqual(resp.json(), {'booking_count': '0/3', 'full': True, 'booked': False})

    def test_toggle_waiting_list_on(self):
        url = reverse('booking:toggle_waiting_list', args=[self.event.id])
        self.assertFalse(WaitingListUser.objects.exists())
        resp = self.client.post(url)

        wl_user = WaitingListUser.objects.first()
        self.assertEqual(wl_user.user, self.user)
        self.assertEqual(wl_user.event, self.event)

        self.assertEqual(resp.context['event'], self.event)
        self.assertEqual(resp.context['on_waiting_list'], True)

    def test_toggle_waiting_list_off(self):
        url = reverse('booking:toggle_waiting_list', args=[self.event.id])
        baker.make(WaitingListUser, user=self.user, event=self.event)
        resp = self.client.post(url)

        self.assertFalse(WaitingListUser.objects.exists())
        self.assertEqual(resp.context['event'], self.event)
        self.assertEqual(resp.context['on_waiting_list'], False)

    def test_toggle_waiting_error_if_outstanding_fees(self):
        baker.make_recipe('booking.booking', user=self.user, cancellation_fee_incurred=True)
        url = reverse('booking:toggle_waiting_list', args=[self.event.id])
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.content.decode('utf-8'), "Action forbidden until outstanding cancellation fees have been resolved")

    def test_booking_details(self):
        """Return correct details to populate the bookings page"""
        url = reverse('booking:booking_details', args=[self.event.id])
        booking = baker.make_recipe(
            'booking.booking', event=self.event, user=self.user, paid=False, status='OPEN'
        )
        resp = self.client.post(url)
        # event has 0 cost, no advance payment required
        self.assertEqual(
            resp.json(),
            {
                'status': 'OPEN',
                'display_status': 'OPEN',
                'no_show': False,
                'display_paid': '<span class="not-confirmed fas fa-times"></span>',
            }
        )

        self.event.cost = 10
        self.event.save()
        resp = self.client.post(url)
        # event has cost, no advance payment required
        self.assertEqual(
            resp.json(),
            {
                'status': 'OPEN',
                'display_status': 'OPEN',
                'no_show': False,
                'display_paid': '<span class="not-confirmed fas fa-times"></span>',
            }
        )

        # no show booking
        booking.no_show = True
        booking.save()
        resp = self.client.post(url)
        # event has cost, no advance payment required
        self.assertEqual(
            resp.json(),
            {
                'status': 'OPEN',
                'display_status': 'CANCELLED',
                'no_show': True,
                'display_paid': '<span class="not-confirmed fas fa-times"></span>',
            }
        )

        # paid booking
        booking.no_show = False
        booking.paid = True
        booking.save()
        resp = self.client.post(url)
        # event has cost, no advance payment required
        self.assertEqual(
            resp.json(),
            {
                'status': 'OPEN',
                'display_status': 'OPEN',
                'no_show': False,
                'display_paid': '<span class="confirmed fas fa-check"></span>',
            }
        )
