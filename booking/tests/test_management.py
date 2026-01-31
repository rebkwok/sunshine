# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from datetime import timezone as dt_timezone

from unittest.mock import patch
from model_bakery import baker

from django.test import TestCase
from django.core import management
from django.core import mail
from django.utils import timezone

from booking.models import Booking, Event


class CancelUnpaidBookingsTests(TestCase):
    def setUp(self):
        self.event = baker.make_recipe(
            "booking.future_EV", event_type="workshop", cost=10, cancellation_period=1
        )
        self.unpaid = baker.make_recipe(
            "booking.booking",
            event=self.event,
            paid=False,
            status="OPEN",
            user__email="unpaid@test.com",
            date_booked=datetime(2015, 2, 9, 18, 0, tzinfo=dt_timezone.utc),
        )
        self.paid = baker.make_recipe(
            "booking.booking",
            event=self.event,
            paid=True,
            status="OPEN",
            user__email="paid@test.com",
            date_booked=datetime(2015, 2, 9, 18, 0, tzinfo=dt_timezone.utc),
        )

    @patch("booking.models.timezone")
    def test_delete_unpaid_bookings(self, mock_tz):
        """
        test unpaid bookings are deleted
        """
        mock_tz.now.return_value = datetime(2015, 2, 10, 19, 0, tzinfo=dt_timezone.utc)
        assert self.unpaid.status == "OPEN", self.unpaid.status
        assert self.paid.status == "OPEN", self.unpaid.status
        assert Booking.objects.count() == 2
        management.call_command("delete_unpaid_bookings")
        assert Booking.objects.count() == 1
        assert Booking.objects.first().id == self.paid.id

    def test_dont_cancel_for_events_in_the_past(self):
        """
        test don't delete for past events
        """
        self.event.date = datetime(2020, 2, 1, 10, 0, tzinfo=dt_timezone.utc)
        self.event.save()
        assert self.unpaid.status == "OPEN", self.unpaid.status
        assert self.paid.status == "OPEN", self.unpaid.status
        assert Booking.objects.count() == 2
        management.call_command("delete_unpaid_bookings")

        assert Booking.objects.count() == 2

    @patch("booking.models.timezone")
    def test_dont_cancel_for_already_cancelled(self, mock_tz):
        """
        ignore already cancelled bookings
        """
        mock_tz.now.return_value = datetime(2015, 2, 10, tzinfo=dt_timezone.utc)
        self.unpaid.status = "CANCELLED"
        self.unpaid.save()
        assert Booking.objects.count() == 2
        management.call_command("delete_unpaid_bookings")
        assert Booking.objects.count() == 2

    def test_dont_cancel_bookings_created_within_past_15_mins(self):
        """
        Avoid immediately cancelling bookings made within the cancellation
        period to allow time for users to make payments
        """
        unpaid_within_15_mins = baker.make_recipe(
            "booking.booking",
            event=self.event,
            paid=False,
            status="OPEN",
            user__email="unpaid@test.com",
            date_booked=timezone.now() - timedelta(minutes=10),
        )
        unpaid_more_than_15_mins = baker.make_recipe(
            "booking.booking",
            event=self.event,
            paid=False,
            status="OPEN",
            user__email="unpaid@test.com",
            date_booked=datetime(2015, 2, 9, 17, 30, tzinfo=dt_timezone.utc),
        )
        unpaid_more_than_15_mins_id = unpaid_more_than_15_mins.id

        management.call_command("delete_unpaid_bookings")
        unpaid_within_15_mins.refresh_from_db()
        assert unpaid_within_15_mins.status == "OPEN"
        assert not Booking.objects.filter(id=unpaid_more_than_15_mins_id).exists()

    def test_cancelling_for_full_event_emails_waiting_list(self):
        """
        Test that deleting a booking for a full event emails
        any users on the waiting list
        """

        # make full event (setup has one paid and one unpaid)
        self.event.max_participants = 2
        self.event.save()

        # make some waiting list users
        for i in range(3):
            baker.make_recipe(
                "booking.waiting_list_user",
                event=self.event,
                user__email="test{}@test.com".format(i),
            )

        management.call_command("delete_unpaid_bookings")
        # one email sent with bcc to waiting list
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            sorted(mail.outbox[0].bcc),
            ["test0@test.com", "test1@test.com", "test2@test.com"],
        )

    def test_cancelling_more_than_one_only_emails_once(self):
        """
        Test that the waiting list is only emailed once if more than one
        booking is deleted
        """

        # make full event (setup has one paid and one unpaid)
        self.event.max_participants = 3
        self.event.save()

        # make another booking that will be cancelled
        baker.make_recipe(
            "booking.booking",
            event=self.event,
            paid=False,
            status="OPEN",
            user__email="unpaid@test.com",
            date_booked=datetime(2015, 2, 9, 18, 0, tzinfo=dt_timezone.utc),
        )
        assert Booking.objects.count() == 3
        # make some waiting list users
        for i in range(3):
            baker.make_recipe(
                "booking.waiting_list_user",
                event=self.event,
                user__email="test{}@test.com".format(i),
            )

        management.call_command("delete_unpaid_bookings")
        assert Booking.objects.count() == 1
        # one email with bcc to waiting list
        # waiting list email sent after the first cancelled booking
        assert len(mail.outbox) == 1
        assert sorted(mail.outbox[0].bcc) == [
            "test0@test.com",
            "test1@test.com",
            "test2@test.com",
        ]

    def test_cancelling_not_full_ev_still_emails_waiting_list(self):
        """
        Test that the waiting list is still emailed if event not full
        """
        # make full event (setup has one paid and one unpaid)
        self.event.max_participants = 3
        self.event.save()
        assert Booking.objects.count() == 2
        # make some waiting list users
        for i in range(3):
            baker.make_recipe(
                "booking.waiting_list_user",
                event=self.event,
                user__email="test{}@test.com".format(i),
            )

        management.call_command("delete_unpaid_bookings")
        assert Booking.objects.count() == 1
        self.assertEqual(len(mail.outbox), 1)

    def test_dont_cancel_bookings_rebooked_within_past_15_mins(self):
        self.unpaid.date_rebooked = timezone.now() - timedelta(minutes=10)
        self.unpaid.save()
        assert Booking.objects.count() == 2

        management.call_command("delete_unpaid_bookings")
        assert Booking.objects.count() == 2

        self.unpaid.date_rebooked = timezone.now() - timedelta(minutes=17)
        self.unpaid.save()

        management.call_command("delete_unpaid_bookings")
        # self.unpaid was rebooked > 15 mins ago
        assert Booking.objects.count() == 1


class EmailRemindersTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Now is 2015, 2, 10, 12, 0
        cls.mock_now = datetime(2015, 2, 10, 12, 0, tzinfo=dt_timezone.utc)
        cls.event_within_48_hrs = baker.make_recipe(
            "booking.future_EV",
            event_type="workshop",
            date=datetime(2015, 2, 12, 11, 0, tzinfo=dt_timezone.utc),
            cost=10,
        )
        cls.event_more_than_48_hrs = baker.make_recipe(
            "booking.future_EV",
            event_type="workshop",
            date=datetime(2015, 2, 12, 14, 0, tzinfo=dt_timezone.utc),
            cost=10,
        )
        cls.past_event = baker.make_recipe(
            "booking.future_EV",
            event_type="workshop",
            date=datetime(2015, 2, 9, 18, 0, tzinfo=dt_timezone.utc),
            cost=10,
        )

    def setUp(self):
        # open bookings made > 6 hrs ago
        for event in Event.objects.all():
            baker.make_recipe(
                "booking.booking",
                event=event,
                user__email="test@test.com",
                date_booked=datetime(2015, 2, 8, 12, 0, tzinfo=dt_timezone.utc),
                paid=True,
            )

    @patch("booking.management.commands.email_reminders.timezone")
    def test_remind_for_event_within_48_hrs(self, mock_tz):
        mock_tz.now.return_value = self.mock_now
        management.call_command("email_reminders")
        self.assertTrue(self.event_within_48_hrs.bookings.first().reminder_sent)
        self.assertFalse(self.event_more_than_48_hrs.bookings.first().reminder_sent)
        self.assertFalse(self.past_event.bookings.first().reminder_sent)
        self.assertEqual(len(mail.outbox), 1)

    @patch("booking.management.commands.email_reminders.timezone")
    def test_no_reminders_for_bookings_with_reminder_sent(self, mock_tz):
        mock_tz.now.return_value = self.mock_now
        booking = self.event_within_48_hrs.bookings.first()
        booking.reminder_sent = True
        booking.save()
        management.call_command("email_reminders")
        self.assertEqual(len(mail.outbox), 0)

    @patch("booking.management.commands.email_reminders.timezone")
    def test_no_reminder_for_booking_within_past_6_hrs(self, mock_tz):
        mock_tz.now.return_value = self.mock_now
        booking = baker.make_recipe(
            "booking.booking",
            event=self.event_within_48_hrs,
            user__email="test1@test.com",
            date_booked=datetime(2015, 2, 10, 7, 0, tzinfo=dt_timezone.utc),
            paid=True,
        )
        management.call_command("email_reminders")
        booking.refresh_from_db()
        self.assertTrue(self.event_within_48_hrs.bookings.first().reminder_sent)
        self.assertFalse(booking.reminder_sent)
        self.assertFalse(self.event_more_than_48_hrs.bookings.first().reminder_sent)
        self.assertFalse(self.past_event.bookings.first().reminder_sent)
        self.assertEqual(len(mail.outbox), 1)

    @patch("booking.management.commands.email_reminders.timezone")
    def test_no_reminder_for_rebooking_within_past_6_hrs(self, mock_tz):
        mock_tz.now.return_value = self.mock_now
        booking = self.event_within_48_hrs.bookings.first()
        self.assertFalse(booking.reminder_sent)
        booking.date_rebooked = datetime(2015, 2, 10, 7, 0, tzinfo=dt_timezone.utc)
        booking.save()
        management.call_command("email_reminders")
        booking.refresh_from_db()
        self.assertFalse(booking.reminder_sent)
        self.assertFalse(self.event_more_than_48_hrs.bookings.first().reminder_sent)
        self.assertFalse(self.past_event.bookings.first().reminder_sent)
        self.assertEqual(len(mail.outbox), 0)

    @patch("booking.management.commands.email_reminders.timezone")
    def test_no_reminder_for_cancelled_event(self, mock_tz):
        mock_tz.now.return_value = self.mock_now
        cancelled_event_within_48_hrs = baker.make_recipe(
            "booking.future_EV",
            event_type="workshop",
            date=datetime(2015, 2, 12, 11, 0, tzinfo=dt_timezone.utc),
            cost=10,
            cancelled=True,
        )
        booking = baker.make_recipe(
            "booking.booking",
            event=cancelled_event_within_48_hrs,
            user__email="test1@test.com",
            date_booked=datetime(2015, 2, 10, 7, 0, tzinfo=dt_timezone.utc),
            paid=True,
        )
        management.call_command("email_reminders")
        booking.refresh_from_db()
        self.assertTrue(self.event_within_48_hrs.bookings.first().reminder_sent)
        self.assertFalse(self.event_more_than_48_hrs.bookings.first().reminder_sent)
        self.assertFalse(self.past_event.bookings.first().reminder_sent)
        self.assertFalse(booking.reminder_sent)

    @patch("booking.management.commands.email_reminders.timezone")
    def test_no_reminder_for_no_show_booking(self, mock_tz):
        mock_tz.now.return_value = self.mock_now

        booking = baker.make_recipe(
            "booking.booking",
            event=self.event_within_48_hrs,
            user__email="test2@test.com",
            date_booked=datetime(2015, 2, 10, 7, 0, tzinfo=dt_timezone.utc),
            no_show=True,
            paid=True,
        )
        management.call_command("email_reminders")
        booking.refresh_from_db()
        self.assertTrue(self.event_within_48_hrs.bookings.first().reminder_sent)
        self.assertFalse(self.event_more_than_48_hrs.bookings.first().reminder_sent)
        self.assertFalse(self.past_event.bookings.first().reminder_sent)
        self.assertFalse(booking.reminder_sent)

    @patch("booking.management.commands.email_reminders.timezone")
    def test_no_reminder_for_cancelled_booking(self, mock_tz):
        mock_tz.now.return_value = self.mock_now

        booking = baker.make_recipe(
            "booking.booking",
            event=self.event_within_48_hrs,
            user__email="test2@test.com",
            date_booked=datetime(2015, 2, 10, 7, 0, tzinfo=dt_timezone.utc),
            status="CANCELLED",
            paid=True,
        )
        management.call_command("email_reminders")
        booking.refresh_from_db()
        self.assertTrue(self.event_within_48_hrs.bookings.first().reminder_sent)
        self.assertFalse(self.event_more_than_48_hrs.bookings.first().reminder_sent)
        self.assertFalse(self.past_event.bookings.first().reminder_sent)
        self.assertFalse(booking.reminder_sent)

    @patch("booking.management.commands.email_reminders.timezone")
    def test_no_reminder_for_unpaid_booking(self, mock_tz):
        mock_tz.now.return_value = self.mock_now

        booking = baker.make_recipe(
            "booking.booking",
            event=self.event_within_48_hrs,
            user__email="test2@test.com",
            date_booked=datetime(2015, 2, 10, 7, 0, tzinfo=dt_timezone.utc),
            paid=False,
        )
        management.call_command("email_reminders")
        booking.refresh_from_db()
        self.assertTrue(self.event_within_48_hrs.bookings.first().reminder_sent)
        self.assertFalse(self.event_more_than_48_hrs.bookings.first().reminder_sent)
        self.assertFalse(self.past_event.bookings.first().reminder_sent)
        self.assertFalse(booking.reminder_sent)
