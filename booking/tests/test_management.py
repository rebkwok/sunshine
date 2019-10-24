# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from unittest.mock import patch
from model_bakery import baker

from django.test import TestCase, override_settings
from django.core import management
from django.core import mail
from django.utils import timezone

from booking.models import Booking, Event


class CancelUnpaidBookingsTests(TestCase):

    def setUp(self):
        self.event = baker.make_recipe(
            'booking.future_EV',
            event_type='workshop',
            date=datetime(2015, 2, 13, 18, 0, tzinfo=timezone.utc),
            cost=10,
            cancellation_period=1
        )
        self.unpaid = baker.make_recipe(
            'booking.booking', event=self.event, paid=False,
            status='OPEN',
            user__email="unpaid@test.com",
            date_booked=datetime(
                2015, 2, 9, 18, 0, tzinfo=timezone.utc
            ),
        )
        self.paid = baker.make_recipe(
            'booking.booking', event=self.event, paid=True,
            status='OPEN',
            user__email="paid@test.com",
            date_booked=datetime(
                2015, 2, 9, 18, 0, tzinfo=timezone.utc
            )
        )

    @patch('booking.management.commands.cancel_unpaid_bookings.timezone')
    def test_cancel_unpaid_bookings(self, mock_tz):
        """
        test unpaid bookings are cancelled
        """
        mock_tz.now.return_value = datetime(
            2015, 2, 10, 19, 0, tzinfo=timezone.utc
        )
        self.assertEquals(
            self.unpaid.status, 'OPEN', self.unpaid.status
        )
        self.assertEquals(
            self.paid.status, 'OPEN', self.paid.status
        )
        management.call_command('cancel_unpaid_bookings')
        # emails are sent to user per cancelled booking
        unpaid_booking = Booking.objects.get(id=self.unpaid.id)
        paid_booking = Booking.objects.get(id=self.paid.id)
        self.assertEquals(len(mail.outbox), 1)
        self.assertEquals(mail.outbox[0].to, ['unpaid@test.com'])
        self.assertEquals(
            unpaid_booking.status, 'CANCELLED', unpaid_booking.status
        )
        self.assertEquals(
            paid_booking.status, 'OPEN', paid_booking.status
        )

    @patch('booking.management.commands.cancel_unpaid_bookings.timezone')
    def test_dont_cancel_for_events_in_the_past(self, mock_tz):
        """
        test don't cancel or send emails for past events
        """
        mock_tz.now.return_value = datetime(
            2016, 2, 10, tzinfo=timezone.utc
        )
        self.assertEquals(
            self.unpaid.status, 'OPEN', self.unpaid.status
        )
        self.assertEquals(
            self.paid.status, 'OPEN', self.paid.status
        )
        self.assertTrue(timezone.now() > self.event.date)
        management.call_command('cancel_unpaid_bookings')
        # emails are sent to user per cancelled booking and studio once
        # for all cancelled bookings
        unpaid_booking = Booking.objects.get(id=self.unpaid.id)
        paid_booking = Booking.objects.get(id=self.paid.id)
        self.assertEquals(len(mail.outbox), 0)
        self.assertEquals(
            unpaid_booking.status, 'OPEN', unpaid_booking.status
        )
        self.assertEquals(
            paid_booking.status, 'OPEN', paid_booking.status
        )

    @patch('booking.management.commands.cancel_unpaid_bookings.timezone')
    def test_dont_cancel_for_already_cancelled(self, mock_tz):
        """
        ignore already cancelled bookings
        """
        mock_tz.now.return_value = datetime(
            2015, 2, 10, tzinfo=timezone.utc
        )
        self.unpaid.status = 'CANCELLED'
        self.unpaid.save()
        self.assertEquals(
            self.unpaid.status, 'CANCELLED', self.unpaid.status
        )
        management.call_command('cancel_unpaid_bookings')
        # emails are sent to user per cancelled booking and studio once
        # for all cancelled bookings
        unpaid_booking = Booking.objects.get(id=self.unpaid.id)
        self.assertEquals(len(mail.outbox), 0)
        self.assertEquals(
            unpaid_booking.status, 'CANCELLED', unpaid_booking.status
        )


    @patch('booking.management.commands.cancel_unpaid_bookings.timezone')
    def test_dont_cancel_non_workshops(self, mock_tz):
        """
        ignore already cancelled bookings
        """
        mock_tz.now.return_value = datetime(
            2015, 2, 10, 19, 0, tzinfo=timezone.utc
        )

        regular_session = baker.make_recipe(
            'booking.future_EV',
            event_type='regular_session',
            date=datetime(2015, 2, 13, 18, 0, tzinfo=timezone.utc),
            cost=10,
            cancellation_period=1
        )
        unpaid_class_booking = baker.make_recipe(
            'booking.booking', event=regular_session, paid=False,
            status='OPEN',
            user__email="unpaid@test.com",
            date_booked=datetime(
                2015, 2, 9, 1, 0, tzinfo=timezone.utc
            ),
        )

        management.call_command('cancel_unpaid_bookings')
        # emails are sent to user per cancelled booking - only self.unpaid
        self.unpaid.refresh_from_db()
        unpaid_class_booking.refresh_from_db()

        self.assertEquals(len(mail.outbox), 1)
        self.assertEquals(self.unpaid.status, 'CANCELLED')
        self.assertEquals(unpaid_class_booking.status, 'OPEN')

    @patch('booking.management.commands.cancel_unpaid_bookings.timezone')
    def test_dont_cancel_bookings_created_within_past_24_hours(self, mock_tz):
        """
        Avoid immediately cancelling bookings made within the cancellation
        period to allow time for users to make payments
        """
        mock_tz.now.return_value = datetime(
            2015, 2, 10, 18, 0, tzinfo=timezone.utc
        )

        unpaid_within_24_hrs = baker.make_recipe(
            'booking.booking', event=self.event, paid=False,
            status='OPEN',
            user__email="unpaid@test.com",
            date_booked=datetime(
                2015, 2, 9, 18, 30, tzinfo=timezone.utc
            ),
        )
        unpaid_more_than_24_hrs = baker.make_recipe(
            'booking.booking', event=self.event, paid=False,
            status='OPEN',
            user__email="unpaid@test.com",
            date_booked=datetime(
                2015, 2, 9, 17, 30, tzinfo=timezone.utc
            ),
        )

        self.assertEquals(unpaid_within_24_hrs.status, 'OPEN')
        self.assertEquals(unpaid_more_than_24_hrs.status, 'OPEN')

        management.call_command('cancel_unpaid_bookings')
        unpaid_within_24_hrs.refresh_from_db()
        unpaid_more_than_24_hrs.refresh_from_db()
        self.assertEquals(unpaid_within_24_hrs.status, 'OPEN')
        self.assertEquals(unpaid_more_than_24_hrs.status, 'CANCELLED')

    @patch('booking.management.commands.cancel_unpaid_bookings.timezone')
    def test_cancelling_for_full_event_emails_waiting_list(self, mock_tz):
        """
        Test that automatically cancelling a booking for a full event emails
        any users on the waiting list
        """
        mock_tz.now.return_value = datetime(
            2015, 2, 13, 17, 15, tzinfo=timezone.utc
        )

        # make full event (setup has one paid and one unpaid)
        # cancellation period =1, date = 2015, 2, 13, 18, 0
        self.event.max_participants = 2
        self.event.save()

        # make some waiting list users
        for i in range(3):
            baker.make_recipe(
                'booking.waiting_list_user', event=self.event,
                user__email='test{}@test.com'.format(i)
            )

        management.call_command('cancel_unpaid_bookings')
        # emails are sent to user per cancelled booking (1) and
        # one email with bcc to waiting list (1)
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(
            sorted(mail.outbox[1].bcc),
            ['test0@test.com', 'test1@test.com', 'test2@test.com']
        )

    @patch('booking.management.commands.cancel_unpaid_bookings.timezone')
    def test_cancelling_more_than_one_only_emails_once(self, mock_tz):
        """
        Test that the waiting list is only emailed once if more than one
        booking is cancelled
        """
        mock_tz.now.return_value = datetime(
            2015, 2, 13, 17, 15, tzinfo=timezone.utc
        )

        # make full event (setup has one paid and one unpaid)
        # cancellation period =1, date = 2015, 2, 13, 18, 0
        self.event.max_participants = 3
        self.event.save()

        # make another booking that will be cancelled
        baker.make_recipe(
            'booking.booking', event=self.event, paid=False,
            status='OPEN',
            user__email="unpaid@test.com",
            date_booked=datetime(
                2015, 2, 9, 18, 0, tzinfo=timezone.utc
            ),
        )

        # make some waiting list users
        for i in range(3):
            baker.make_recipe(
                'booking.waiting_list_user', event=self.event,
                user__email='test{}@test.com'.format(i)
            )

        management.call_command('cancel_unpaid_bookings')
        # emails are sent to user per cancelled booking (2) and
        # one email with bcc to waiting list (1)
        # waiting list email sent after the first cancelled booking
        self.assertEqual(len(mail.outbox), 3)
        self.assertEqual(
            sorted(mail.outbox[1].bcc),
            ['test0@test.com', 'test1@test.com', 'test2@test.com']
        )
        for email in [mail.outbox[0], mail.outbox[2]]:
            self.assertEqual(email.bcc, [])

        self.assertEqual(Booking.objects.filter(status='CANCELLED').count(), 2)

    @patch('booking.management.commands.cancel_unpaid_bookings.timezone')
    def test_cancelling_not_full_ev_doesnt_email_waiting_list(self, mock_tz):
        """
        Test that the waiting list is not emailed if event not full
        """
        mock_tz.now.return_value = datetime(
            2015, 2, 13, 17, 15, tzinfo=timezone.utc
        )

        # make full event (setup has one paid and one unpaid)
        # cancellation period =1, date = 2015, 2, 13, 18, 0
        self.event.max_participants = 3
        self.event.save()

        # make some waiting list users
        for i in range(3):
            baker.make_recipe(
                'booking.waiting_list_user', event=self.event,
                user__email='test{}@test.com'.format(i)
            )

        management.call_command('cancel_unpaid_bookings')
        # emails are sent to user per cancelled booking (1) only
        self.assertEqual(len(mail.outbox), 1)

    @patch('booking.management.commands.cancel_unpaid_bookings.timezone')
    def test_dont_cancel_bookings_rebooked_within_past_24_hours(self, mock_tz):
        mock_tz.now.return_value = datetime(
            2015, 2, 10, 18, 0, tzinfo=timezone.utc
        )
        self.unpaid.date_rebooked = datetime(
            2015, 2, 9, 18, 30, tzinfo=timezone.utc
        )
        self.unpaid.save()

        self.assertEquals(self.unpaid.status, 'OPEN')

        management.call_command('cancel_unpaid_bookings')
        # self.unpaid was booked > 6 hrs ago
        self.assertTrue(
            self.unpaid.date_booked <= (timezone.now() - timedelta(hours=6))
        )
        self.unpaid.refresh_from_db()
        # but still open
        self.assertEquals(self.unpaid.status, 'OPEN')

        # move time on one hour and try again
        mock_tz.now.return_value = datetime(
            2015, 2, 10, 19, 0, tzinfo=timezone.utc
        )
        management.call_command('cancel_unpaid_bookings')
        # self.unpaid was rebooked > 6 hrs ago
        self.assertTrue(
            self.unpaid.date_rebooked <= (timezone.now() - timedelta(hours=6))
        )
        self.unpaid.refresh_from_db()
        # now cancelled
        self.assertEquals(self.unpaid.status, 'CANCELLED')


class EmailRemindersTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        # Now is 2015, 2, 10, 12, 0
        cls.mock_now = datetime(2015, 2, 10, 12, 0, tzinfo=timezone.utc)
        cls.event_within_48_hrs = baker.make_recipe(
            'booking.future_EV',
            event_type='workshop',
            date=datetime(2015, 2, 12, 11, 0, tzinfo=timezone.utc),
            cost=10,
        )
        cls.event_more_than_48_hrs = baker.make_recipe(
            'booking.future_EV',
            event_type='workshop',
            date=datetime(2015, 2, 12, 14, 0, tzinfo=timezone.utc),
            cost=10,
        )
        cls.past_event = baker.make_recipe(
            'booking.future_EV',
            event_type='workshop',
            date=datetime(2015, 2, 9, 18, 0, tzinfo=timezone.utc),
            cost=10,
        )

    def setUp(self):
        # open bookings made > 6 hrs ago
        for event in Event.objects.all():
            baker.make_recipe(
                'booking.booking', event=event, user__email='test@test.com',
                date_booked=datetime(2015, 2, 8, 12, 0, tzinfo=timezone.utc)
            )

    @patch('booking.management.commands.email_reminders.timezone')
    def test_remind_for_event_within_48_hrs(self, mock_tz):
        mock_tz.now.return_value = self.mock_now
        management.call_command('email_reminders')
        self.assertTrue(self.event_within_48_hrs.bookings.first().reminder_sent)
        self.assertFalse(self.event_more_than_48_hrs.bookings.first().reminder_sent)
        self.assertFalse(self.past_event.bookings.first().reminder_sent)
        self.assertEqual(len(mail.outbox), 1)

    @patch('booking.management.commands.email_reminders.timezone')
    def test_no_reminders_for_bookings_with_reminder_sent(self, mock_tz):
        mock_tz.now.return_value = self.mock_now
        booking = self.event_within_48_hrs.bookings.first()
        booking.reminder_sent = True
        booking.save()
        management.call_command('email_reminders')
        self.assertEqual(len(mail.outbox), 0)

    @patch('booking.management.commands.email_reminders.timezone')
    def test_no_reminder_for_booking_within_past_6_hrs(self, mock_tz):
        mock_tz.now.return_value = self.mock_now
        booking = baker.make_recipe(
            'booking.booking', event=self.event_within_48_hrs, user__email='test1@test.com',
            date_booked=datetime(2015, 2, 10, 7, 0, tzinfo=timezone.utc)
        )
        management.call_command('email_reminders')
        booking.refresh_from_db()
        self.assertTrue(self.event_within_48_hrs.bookings.first().reminder_sent)
        self.assertFalse(booking.reminder_sent)
        self.assertFalse(self.event_more_than_48_hrs.bookings.first().reminder_sent)
        self.assertFalse(self.past_event.bookings.first().reminder_sent)
        self.assertEqual(len(mail.outbox), 1)

    @patch('booking.management.commands.email_reminders.timezone')
    def test_no_reminder_for_rebooking_within_past_6_hrs(self, mock_tz):
        mock_tz.now.return_value = self.mock_now
        booking = self.event_within_48_hrs.bookings.first()
        self.assertFalse(booking.reminder_sent)
        booking.date_rebooked = datetime(2015, 2, 10, 7, 0, tzinfo=timezone.utc)
        booking.save()
        management.call_command('email_reminders')
        booking.refresh_from_db()
        self.assertFalse(booking.reminder_sent)
        self.assertFalse(self.event_more_than_48_hrs.bookings.first().reminder_sent)
        self.assertFalse(self.past_event.bookings.first().reminder_sent)
        self.assertEqual(len(mail.outbox), 0)

    @patch('booking.management.commands.email_reminders.timezone')
    def test_no_reminder_for_cancelled_event(self, mock_tz):
        mock_tz.now.return_value = self.mock_now
        cancelled_event_within_48_hrs = baker.make_recipe(
            'booking.future_EV',
            event_type='workshop',
            date=datetime(2015, 2, 12, 11, 0, tzinfo=timezone.utc),
            cost=10,
            cancelled=True
        )
        booking = baker.make_recipe(
            'booking.booking', event=cancelled_event_within_48_hrs, user__email='test1@test.com',
            date_booked=datetime(2015, 2, 10, 7, 0, tzinfo=timezone.utc)
        )
        management.call_command('email_reminders')
        booking.refresh_from_db()
        self.assertTrue(self.event_within_48_hrs.bookings.first().reminder_sent)
        self.assertFalse(self.event_more_than_48_hrs.bookings.first().reminder_sent)
        self.assertFalse(self.past_event.bookings.first().reminder_sent)
        self.assertFalse(booking.reminder_sent)

    @patch('booking.management.commands.email_reminders.timezone')
    def test_no_reminder_for_no_show_booking(self, mock_tz):
        mock_tz.now.return_value = self.mock_now

        booking = baker.make_recipe(
            'booking.booking', event=self.event_within_48_hrs, user__email='test2@test.com',
            date_booked=datetime(2015, 2, 10, 7, 0, tzinfo=timezone.utc), no_show=True
        )
        management.call_command('email_reminders')
        booking.refresh_from_db()
        self.assertTrue(self.event_within_48_hrs.bookings.first().reminder_sent)
        self.assertFalse(self.event_more_than_48_hrs.bookings.first().reminder_sent)
        self.assertFalse(self.past_event.bookings.first().reminder_sent)
        self.assertFalse(booking.reminder_sent)

    @patch('booking.management.commands.email_reminders.timezone')
    def test_no_reminder_for_cancelled_booking(self, mock_tz):
        mock_tz.now.return_value = self.mock_now

        booking = baker.make_recipe(
            'booking.booking', event=self.event_within_48_hrs, user__email='test2@test.com',
            date_booked=datetime(2015, 2, 10, 7, 0, tzinfo=timezone.utc), status='CANCELLED'
        )
        management.call_command('email_reminders')
        booking.refresh_from_db()
        self.assertTrue(self.event_within_48_hrs.bookings.first().reminder_sent)
        self.assertFalse(self.event_more_than_48_hrs.bookings.first().reminder_sent)
        self.assertFalse(self.past_event.bookings.first().reminder_sent)
        self.assertFalse(booking.reminder_sent)
