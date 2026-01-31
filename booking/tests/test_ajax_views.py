# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from datetime import timezone as dt_timezone

from unittest.mock import patch
from model_bakery import baker

from django.conf import settings
from django.core import mail
from django.core.handlers.wsgi import WSGIRequest
from django.urls import reverse
from django.test import override_settings, TestCase
from django.utils import timezone

from conftest import make_data_privacy_agreement
from stripe_payments.models import Invoice

from ..models import Event, Booking, GiftVoucher, Membership, WaitingListUser


class BookingToggleAjaxViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = baker.make_recipe(
            "booking.user", email="test@test.com", password="test"
        )
        cls.event = baker.make_recipe(
            "booking.future_PC",
            email_studio_when_booked=True,
            cost=5,
            max_participants=3,
        )
        cls.url = reverse("booking:toggle_booking", args=[cls.event.id])

    def setUp(self):
        super().setUp()
        make_data_privacy_agreement(self.user)
        self.client.force_login(self.user)

    def test_create_booking(self):
        """
        Test creating a booking
        """
        self.assertEqual(Booking.objects.all().count(), 0)
        resp = self.client.post(self.url)
        self.assertEqual(Booking.objects.all().count(), 1)
        self.assertEqual(resp.context["alert_message"]["message"], "Added to basket.")
        self.assertFalse(Booking.objects.first().paid)

        # no emails sent as booking not paid
        # email to student and studio
        self.assertEqual(len(mail.outbox), 0)

    def test_create_booking_membership_available(self):
        # membership available
        baker.make(
            Membership,
            user=self.user,
            paid=True,
            month=self.event.date.month,
            year=self.event.date.year,
        )
        assert not Booking.objects.all().exists()
        resp = self.client.post(self.url)
        assert resp.context["alert_message"]["message"] == "Booked."
        assert Booking.objects.first().paid

        # no emails sent as booking not paid
        # email to student and studio
        self.assertEqual(len(mail.outbox), 2)

    def test_create_booking_sends_email_to_studio_if_set(self):
        """
        Test creating a booking send email to user and studio if flag sent on
        event
        """
        event = baker.make_recipe(
            "booking.future_PC",
            cost=5,
            max_participants=3,
            email_studio_when_booked=False,
        )
        # membership available
        baker.make(
            Membership,
            user=self.user,
            paid=True,
            month=event.date.month,
            year=event.date.year,
        )
        url = reverse("booking:toggle_booking", args=[event.id])
        self.assertEqual(Booking.objects.all().count(), 0)
        self.client.post(url)
        self.assertEqual(Booking.objects.all().count(), 1)
        # email to student only
        self.assertEqual(len(mail.outbox), 1)

    def test_cannot_book_for_full_event(self):
        """
        Test trying create booking for a full event returns 400
        """
        users = baker.make_recipe("booking.user", _quantity=3)
        for user in users:
            baker.make_recipe("booking.booking", event=self.event, user=user)
        # check event is full; we need to get the event again as spaces_left is
        # cached property
        event = Event.objects.get(id=self.event.id)
        self.assertEqual(event.spaces_left, 0)
        # try to book for event
        resp = self.client.post(self.url)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.content.decode("utf-8"), "Sorry, this class is now full")

    def test_cannot_book_for_cancelled_event(self):
        """cannot create booking for a full event"""
        event = baker.make_recipe(
            "booking.future_EV", max_participants=3, cancelled=True, cost=5
        )
        url = reverse("booking:toggle_booking", args=[event.id])
        # try to book for event
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(
            resp.content.decode("utf-8"), "Sorry, this workshop has been cancelled"
        )

    def test_cancelled_booking_can_be_rebooked(self):
        """
        Test can load create booking page with a cancelled booking
        """
        booking = baker.make_recipe(
            "booking.booking", event=self.event, user=self.user, status="CANCELLED"
        )
        # try to book again
        resp = self.client.post(self.url)

        booking.refresh_from_db()
        self.assertEqual(booking.status, "OPEN")
        self.assertIsNotNone(booking.date_rebooked)

        self.assertEqual(resp.context["alert_message"]["message"], "Added to basket.")

    def test_rebook_no_show_booking(self):
        """
        Test can rebook a booking marked as no_show
        """
        pclass = baker.make_recipe(
            "booking.future_PC", allow_booking_cancellation=False, cost=10
        )
        url = reverse("booking:toggle_booking", args=[pclass.id])

        # book for non-refundable event and mark as no_show
        booking = baker.make_recipe(
            "booking.booking", user=self.user, event=pclass, paid=True, no_show=True
        )
        self.assertIsNone(booking.date_rebooked)

        # try to book again
        resp = self.client.post(url)
        booking.refresh_from_db()
        self.assertEqual("OPEN", booking.status)
        self.assertFalse(booking.no_show)
        self.assertIsNotNone(booking.date_rebooked)
        self.assertEqual(resp.context["alert_message"]["message"], "Booked.")

        # emails sent to student and studio
        self.assertEqual(len(mail.outbox), 2)
        email = mail.outbox[0]
        self.assertEqual(email.to, ["test@test.com"])

    def test_create_booking_user_on_waiting_list(self):
        """
        Test creating a booking for a user on the waiting list deletes waiting list
        """
        baker.make(WaitingListUser, event=self.event, user=self.user)
        baker.make(WaitingListUser, event=self.event)
        baker.make(WaitingListUser, user=self.user)
        self.assertEqual(Booking.objects.all().count(), 0)
        self.client.force_login(self.user)

        self.client.post(self.url)
        self.assertEqual(Booking.objects.all().count(), 1)
        # the waiting list user for this user and event only has been deleted
        self.assertEqual(WaitingListUser.objects.all().count(), 2)
        self.assertFalse(
            WaitingListUser.objects.filter(user=self.user, event=self.event).exists()
        )

    def test_create_booking_with_membership(self):
        event = baker.make_recipe("booking.future_PC")
        url = reverse("booking:toggle_booking", args=[event.id])
        membership = baker.make(
            Membership,
            user=self.user,
            paid=True,
            month=event.date.month,
            year=event.date.year,
        )
        resp = self.client.post(url)
        assert resp.context["alert_message"]["message"] == "Booked."
        booking = Booking.objects.latest("id")
        assert booking.event == event
        assert booking.status == "OPEN"
        assert booking.membership == membership

    def test_cancel_booking(self):
        """
        Toggle open paid booking to cancelled
        """
        booking = baker.make_recipe(
            "booking.booking", user=self.user, event=self.event, paid=True
        )
        self.client.login(username=self.user.username, password="test")
        resp = self.client.post(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["alert_message"]["message"], "Cancelled.")
        booking.refresh_from_db()
        self.assertEqual(booking.status, "CANCELLED")

    def test_go_to_basket(self):
        """
        Toggle open, unpaid booking - goes to basket
        """
        baker.make_recipe("booking.booking", user=self.user, event=self.event)
        self.client.login(username=self.user.username, password="test")
        resp = self.client.post(self.url)
        assert resp.status_code == 200
        json_resp = resp.json()
        assert json_resp["redirect"]
        assert json_resp["url"] == reverse("booking:shopping_basket")

    @patch("booking.models.timezone.now")
    def test_cancel_booking_within_cancellation_period(self, mock_now):
        """
        Toggle booking to no-show
        """
        mock_now.return_value = datetime(2018, 1, 1, 9, tzinfo=dt_timezone.utc)
        event = baker.make_recipe(
            "booking.future_PC", date=datetime(2018, 1, 1, 10, tzinfo=dt_timezone.utc)
        )
        url = reverse("booking:toggle_booking", args=[event.id])

        booking = baker.make_recipe(
            "booking.booking",
            user=self.user,
            event=event,
            date_booked=datetime(2018, 1, 1, 8, 44, tzinfo=dt_timezone.utc),
            paid=True,
        )  # booked and paid within cancellation period
        self.client.login(username=self.user.username, password="test")
        resp = self.client.post(url)
        assert resp.status_code == 200
        assert resp.context["alert_message"]["message"] == (
            "Cancelled. Please note that this booking is not eligible for "
            "refunds as the allowed cancellation period has passed."
        )
        booking.refresh_from_db()
        assert booking.status == "OPEN"
        assert booking.no_show

    def test_cancel_booking_cancellation_not_allowed(self):
        """
        Toggle booking to no-show
        """
        event = baker.make_recipe("booking.future_PC", allow_booking_cancellation=False)
        url = reverse("booking:toggle_booking", args=[event.id])

        booking = baker.make_recipe(
            "booking.booking",
            user=self.user,
            event=event,
            date_booked=datetime(2018, 1, 1, 8, 44, tzinfo=dt_timezone.utc),
            paid=True,
        )
        self.client.login(username=self.user.username, password="test")
        resp = self.client.post(url)
        assert resp.context["alert_message"]["message"] == (
            "Cancelled. Please note that this booking is not eligible for refunds or transfer credit."
        )
        booking.refresh_from_db()
        assert booking.status == "OPEN"
        assert booking.no_show

    def test_cancel_booking_made_with_membership(self):
        event = baker.make_recipe("booking.future_PC")
        url = reverse("booking:toggle_booking", args=[event.id])
        self.client.login(username=self.user.username, password="test")

        membership = baker.make(Membership, user=self.user, paid=True)
        booking = baker.make_recipe(
            "booking.booking",
            user=self.user,
            event=event,
            date_booked=datetime(2018, 1, 1, 8, 56, tzinfo=dt_timezone.utc),
            paid=True,
            membership=membership,
        )

        resp = self.client.post(url)
        booking.refresh_from_db()
        assert resp.context["alert_message"]["message"] == "Cancelled."
        assert booking.status == "CANCELLED"
        assert not booking.no_show
        assert booking.membership is None

    @patch("booking.models.timezone.now")
    def test_cancel_booking_made_with_membership_within_5_mins_during_cancellation_period(
        self, mock_now
    ):
        """
        Cancelling within 5 mins allows proper cancelling
        """
        mock_now.return_value = datetime(2018, 1, 1, 9, tzinfo=dt_timezone.utc)
        event = baker.make_recipe(
            "booking.future_PC", date=datetime(2018, 1, 1, 10, tzinfo=dt_timezone.utc)
        )
        url = reverse("booking:toggle_booking", args=[event.id])
        self.client.login(username=self.user.username, password="test")

        membership = baker.make(Membership, user=self.user)
        booking = baker.make_recipe(
            "booking.booking",
            user=self.user,
            event=event,
            date_booked=datetime(2018, 1, 1, 8, 56, tzinfo=dt_timezone.utc),
            paid=True,
            membership=membership,
        )

        resp = self.client.post(url)
        booking.refresh_from_db()
        self.assertEqual(resp.context["alert_message"]["message"], "Cancelled.")
        self.assertEqual(booking.status, "CANCELLED")
        self.assertFalse(booking.no_show)

    @patch("booking.models.timezone.now")
    def test_cancel_rebooking_within_5_mins_during_cancellation_period(self, mock_now):
        """
        Cancelling within 5 mins of rebooking allows proper cancelling
        """
        mock_now.return_value = datetime(2018, 1, 1, 9, tzinfo=dt_timezone.utc)
        event = baker.make_recipe(
            "booking.future_PC", date=datetime(2018, 1, 1, 10, tzinfo=dt_timezone.utc)
        )
        url = reverse("booking:toggle_booking", args=[event.id])
        self.client.login(username=self.user.username, password="test")

        membership = baker.make(Membership, user=self.user)
        booking = baker.make_recipe(
            "booking.booking",
            user=self.user,
            event=event,
            date_booked=datetime(2018, 1, 1, 5, 0, tzinfo=dt_timezone.utc),
            date_rebooked=datetime(2018, 1, 1, 8, 56, tzinfo=dt_timezone.utc),
            paid=True,
            membership=membership,
        )
        resp = self.client.post(url)
        booking.refresh_from_db()
        self.assertEqual(resp.context["alert_message"]["message"], "Cancelled.")
        self.assertEqual(booking.status, "CANCELLED")
        self.assertFalse(booking.no_show)

    @patch("booking.views.booking_helpers.process_refund")
    def test_cancel_booking_paid_with_stripe(self, mock_process_refund):
        mock_process_refund.return_value = True
        event = baker.make_recipe("booking.future_PC")
        url = reverse("booking:toggle_booking", args=[event.id])
        self.client.login(username=self.user.username, password="test")

        invoice = baker.make(
            Invoice,
            paid=True,
            username=self.user.email,
            invoice_id="inv123",
            stripe_payment_intent_id="pi_123",
        )
        booking = baker.make_recipe(
            "booking.booking",
            user=self.user,
            event=event,
            date_booked=datetime(2018, 1, 1, 8, 56, tzinfo=dt_timezone.utc),
            paid=True,
            invoice=invoice,
        )

        resp = self.client.post(url)
        booking.refresh_from_db()
        assert (
            resp.context["alert_message"]["message"] == "Cancelled. Refund processing."
        )
        assert booking.status == "CANCELLED"
        assert not booking.no_show
        assert not booking.paid

        # test that the process_refund function was called as expected
        mock_process_refund.assert_called_once()
        assert len(mock_process_refund.call_args[0]) == 2
        call_args = mock_process_refund.call_args[0]
        assert isinstance(call_args[0], WSGIRequest)
        assert call_args[1] == booking

    def test_cancel_full_booking_emails_waiting_list(self):
        """
        Toggle booking to cancelled
        """
        booking = baker.make_recipe(
            "booking.booking", user=self.user, event=self.event, paid=True
        )
        baker.make_recipe("booking.booking", event=self.event, _quantity=2)
        for i in range(3):
            baker.make(
                WaitingListUser,
                event=self.event,
                user__email="test{}@test.test".format(i),
            )

        event = Event.objects.get(id=self.event.id)
        self.assertFalse(event.spaces_left)

        self.client.login(username=self.user.username, password="test")
        resp = self.client.post(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["alert_message"]["message"], "Cancelled.")
        booking.refresh_from_db()
        self.assertEqual(booking.status, "CANCELLED")
        self.assertEqual(
            len(mail.outbox), 3
        )  # email to user, studio and 1 to all 3 waiting list users
        wl_email = mail.outbox[2]
        self.assertEqual(len(wl_email.bcc), 3)

    @override_settings(AUTO_BOOK_EMAILS=["test1@test.test"])
    def test_cancel_full_booking_emails_auto_book_user_on_waiting_list(self):
        # if autobook user is on waiting list, create booking, email user, DO NOT email rest of waiting list
        baker.make_recipe(
            "booking.booking", user=self.user, event=self.event, paid=True
        )
        baker.make_recipe("booking.booking", event=self.event, _quantity=2)
        for i in range(3):
            baker.make(
                WaitingListUser,
                event=self.event,
                user__email="test{}@test.test".format(i),
            )

        self.assertFalse(self.event.spaces_left)
        self.assertFalse(
            "test1@test.test"
            in self.event.bookings.filter(status="OPEN", no_show=False).values_list(
                "user__email", flat=True
            )
        )

        # cancel booking
        self.client.login(username=self.user.username, password="test")
        self.client.post(self.url)

        self.event.refresh_from_db()
        # still no spaces left because autobook user has been booked
        self.assertFalse(self.event.spaces_left)
        self.assertTrue(
            "test1@test.test"
            in self.event.bookings.filter(status="OPEN", no_show=False).values_list(
                "user__email", flat=True
            )
        )
        self.assertFalse(
            WaitingListUser.objects.filter(user__email="test1@test.test").exists()
        )

        # email to user, studio and 1 to autobook user. No waiting list emails
        self.assertEqual(len(mail.outbox), 3)
        self.assertEqual(
            [[self.user.email], [settings.DEFAULT_STUDIO_EMAIL], ["test1@test.test"]],
            [mail.to for mail in mail.outbox],
        )
        self.assertIn("You have been booked into", mail.outbox[2].subject)

    @override_settings(AUTO_BOOK_EMAILS=["test1@test.test", "test0@test.test"])
    def test_cancel_full_booking_emails_auto_book_user_on_waiting_list_multiple_users(
        self,
    ):
        # if autobook user is on waiting list, create booking for first autobook user, email user,
        # DO NOT email rest of waiting list
        # if autobook user is on waiting list, create booking, email user, DO NOT email rest of waiting list
        baker.make_recipe(
            "booking.booking", user=self.user, event=self.event, paid=True
        )
        baker.make_recipe("booking.booking", event=self.event, _quantity=2)
        for i in range(3):
            baker.make(
                WaitingListUser,
                event=self.event,
                user__email="test{}@test.test".format(i),
            )

        self.assertFalse(self.event.spaces_left)
        self.assertFalse(
            "test1@test.test"
            in self.event.bookings.filter(status="OPEN", no_show=False).values_list(
                "user__email", flat=True
            )
        )

        # cancel booking
        self.client.login(username=self.user.username, password="test")
        self.client.post(self.url)

        self.event.refresh_from_db()
        # still no spaces left because autobook user has been booked
        self.assertFalse(self.event.spaces_left)
        # Only first autobook user booked
        open_booking_emails = self.event.bookings.filter(
            status="OPEN", no_show=False
        ).values_list("user__email", flat=True)
        self.assertTrue("test1@test.test" in open_booking_emails)
        self.assertFalse(
            WaitingListUser.objects.filter(user__email="test1@test.test").exists()
        )
        self.assertFalse("test0@test.test" in open_booking_emails)
        self.assertTrue(
            WaitingListUser.objects.filter(user__email="test0@test.test").exists()
        )

        # email to user, studio and 1 to autobook user. No waiting list emails
        self.assertEqual(len(mail.outbox), 3)
        self.assertEqual(
            [[self.user.email], [settings.DEFAULT_STUDIO_EMAIL], ["test1@test.test"]],
            [mail.to for mail in mail.outbox],
        )
        self.assertIn("You have been booked into", mail.outbox[2].subject)

    @override_settings(AUTO_BOOK_EMAILS=["test1@test.test"])
    def test_cancel_full_booking_emails_auto_book_user_on_waiting_list_previously_cancelled(
        self,
    ):
        # change existing booking to open, email user, DO NOT email rest of waiting list
        baker.make_recipe(
            "booking.booking", user=self.user, event=self.event, paid=True
        )
        cancelled_user = baker.make_recipe("booking.user", email="test1@test.test")
        booking = baker.make_recipe(
            "booking.booking", user=cancelled_user, event=self.event, status="CANCELLED"
        )
        self.assertIsNone(booking.date_rebooked)
        baker.make_recipe("booking.booking", event=self.event, _quantity=2)
        baker.make(WaitingListUser, event=self.event, user=cancelled_user)
        for i in range(2, 4):
            baker.make(
                WaitingListUser,
                event=self.event,
                user__email="test{}@test.test".format(i),
            )

        self.assertFalse(self.event.spaces_left)
        self.assertFalse(
            "test1@test.test"
            in self.event.bookings.filter(status="OPEN", no_show=False).values_list(
                "user__email", flat=True
            )
        )

        # cancel booking
        self.client.login(username=self.user.username, password="test")
        self.client.post(self.url)

        self.event.refresh_from_db()
        # still no spaces left because autobook user has been booked
        self.assertFalse(self.event.spaces_left)
        # Only first autobook user booked
        open_booking_emails = self.event.bookings.filter(
            status="OPEN", no_show=False
        ).values_list("user__email", flat=True)
        self.assertTrue("test1@test.test" in open_booking_emails)
        self.assertFalse(
            WaitingListUser.objects.filter(user__email="test1@test.test").exists()
        )
        # booking has been reopened
        booking.refresh_from_db()
        self.assertEqual(booking.status, "OPEN")
        self.assertIsNotNone(booking.date_rebooked)

        # email to user, studio and 1 to autobook user. No waiting list emails
        self.assertEqual(len(mail.outbox), 3)
        self.assertEqual(
            [[self.user.email], [settings.DEFAULT_STUDIO_EMAIL], ["test1@test.test"]],
            [mail.to for mail in mail.outbox],
        )
        self.assertIn("You have been booked into", mail.outbox[2].subject)

    @override_settings(AUTO_BOOK_EMAILS=["test1@test.test"])
    def test_cancel_full_booking_emails_auto_book_user_on_waiting_list_previously_no_show(
        self,
    ):
        # change existing booking to open/not no_show, email user, DO NOT email rest of waiting list
        baker.make_recipe(
            "booking.booking", user=self.user, event=self.event, paid=True
        )
        no_show_user = baker.make_recipe("booking.user", email="test1@test.test")
        booking = baker.make_recipe(
            "booking.booking",
            user=no_show_user,
            event=self.event,
            status="OPEN",
            no_show=True,
        )
        self.assertIsNone(booking.date_rebooked)
        baker.make_recipe("booking.booking", event=self.event, _quantity=2)
        baker.make(WaitingListUser, event=self.event, user=no_show_user)
        for i in range(2, 4):
            baker.make(
                WaitingListUser,
                event=self.event,
                user__email="test{}@test.test".format(i),
            )

        self.assertFalse(self.event.spaces_left)
        self.assertFalse(
            "test1@test.test"
            in self.event.bookings.filter(status="OPEN", no_show=False).values_list(
                "user__email", flat=True
            )
        )

        # cancel booking
        self.client.login(username=self.user.username, password="test")
        self.client.post(self.url)

        self.event.refresh_from_db()
        # still no spaces left because autobook user has been booked
        self.assertFalse(self.event.spaces_left)
        # Only first autobook user booked
        open_booking_emails = self.event.bookings.filter(
            status="OPEN", no_show=False
        ).values_list("user__email", flat=True)
        self.assertTrue("test1@test.test" in open_booking_emails)
        self.assertFalse(
            WaitingListUser.objects.filter(user__email="test1@test.test").exists()
        )
        # booking has been reopened
        booking.refresh_from_db()
        self.assertEqual(booking.status, "OPEN")
        self.assertIsNotNone(booking.date_rebooked)

        # email to user, studio and 1 to autobook user. No waiting list emails
        self.assertEqual(len(mail.outbox), 3)
        self.assertEqual(
            [[self.user.email], [settings.DEFAULT_STUDIO_EMAIL], ["test1@test.test"]],
            [mail.to for mail in mail.outbox],
        )
        self.assertIn("You have been booked into", mail.outbox[2].subject)

    @override_settings(AUTO_BOOK_EMAILS=["test1@test.test"])
    def test_cancel_full_booking_emails_auto_book_user_on_waiting_list_already_booked(
        self,
    ):
        # leave existing booking as is, do not email autobook user, email rest of waiting list
        baker.make_recipe(
            "booking.booking", user=self.user, event=self.event, paid=True
        )
        open_user = baker.make_recipe("booking.user", email="test1@test.test")
        baker.make_recipe(
            "booking.booking", user=open_user, event=self.event, status="OPEN"
        )
        baker.make_recipe("booking.booking", event=self.event, _quantity=1)
        baker.make(WaitingListUser, event=self.event, user=open_user)
        for i in range(2, 4):
            baker.make(
                WaitingListUser,
                event=self.event,
                user__email="test{}@test.test".format(i),
            )

        self.assertFalse(self.event.spaces_left)
        self.assertTrue(
            "test1@test.test"
            in self.event.bookings.filter(status="OPEN", no_show=False).values_list(
                "user__email", flat=True
            )
        )

        # cancel booking
        self.client.login(username=self.user.username, password="test")
        self.client.post(self.url)

        self.event.refresh_from_db()
        # a space left because autobook user was already booked
        self.assertEqual(self.event.spaces_left, 1)

        open_booking_emails = self.event.bookings.filter(
            status="OPEN", no_show=False
        ).values_list("user__email", flat=True)
        self.assertTrue("test1@test.test" in open_booking_emails)
        # user removed from waiting list
        self.assertFalse(
            WaitingListUser.objects.filter(user__email="test1@test.test").exists()
        )

        # email to user, studio and 1 to all waiting list emails
        self.assertEqual(len(mail.outbox), 3)
        self.assertEqual(
            [[self.user.email], [settings.DEFAULT_STUDIO_EMAIL], []],
            [mail.to for mail in mail.outbox],
        )
        self.assertIn("space now available", mail.outbox[2].subject)
        self.assertEqual(mail.outbox[2].bcc, ["test2@test.test", "test3@test.test"])

    @override_settings(AUTO_BOOK_EMAILS=["test1@test.test", "test2@test.test"])
    def test_cancel_full_booking_emails_auto_book_user_on_waiting_list_already_booked_multiple_users(
        self,
    ):
        # First autobook user of multiple is already booked
        # Leave existing booking as is, do not email first user
        # Create second user's booking and email, DO NOT email rest of waiting list
        baker.make_recipe(
            "booking.booking", user=self.user, event=self.event, paid=True
        )
        open_user = baker.make_recipe("booking.user", email="test1@test.test")
        baker.make_recipe(
            "booking.booking", user=open_user, event=self.event, status="OPEN"
        )
        baker.make_recipe("booking.booking", event=self.event, _quantity=1)
        for i in range(2, 4):
            baker.make(
                WaitingListUser,
                event=self.event,
                user__email="test{}@test.test".format(i),
            )

        self.assertFalse(self.event.spaces_left)
        self.assertTrue(
            "test1@test.test"
            in self.event.bookings.filter(status="OPEN", no_show=False).values_list(
                "user__email", flat=True
            )
        )

        # cancel booking
        self.client.login(username=self.user.username, password="test")
        self.client.post(self.url)

        self.event.refresh_from_db()
        # no space left because 2nd autobook user booked
        self.assertFalse(self.event.spaces_left)

        open_booking_emails = self.event.bookings.filter(
            status="OPEN", no_show=False
        ).values_list("user__email", flat=True)
        self.assertTrue("test1@test.test" in open_booking_emails)
        self.assertTrue("test2@test.test" in open_booking_emails)
        # 2nd user removed from waiting list
        self.assertFalse(
            WaitingListUser.objects.filter(user__email="test2@test.test").exists()
        )

        # email to cancelled user, studio and 2nd autobook user
        self.assertEqual(len(mail.outbox), 3)
        self.assertEqual(
            [[self.user.email], [settings.DEFAULT_STUDIO_EMAIL], ["test2@test.test"]],
            [mail.to for mail in mail.outbox],
        )

    @override_settings(AUTO_BOOK_EMAILS=["test1@test.test"])
    def test_cancel_full_booking_emails_auto_book_user_not_on_waiting_list(self):
        # Email waiting list as normal
        # leave existing booking as is, do not email autobook user, email rest of waiting list
        baker.make_recipe(
            "booking.booking", user=self.user, event=self.event, paid=True
        )
        baker.make_recipe(
            "booking.booking",
            user__email="test1@test.test",
            event=self.event,
            status="OPEN",
        )
        baker.make_recipe("booking.booking", event=self.event, _quantity=1)

        for i in range(2, 4):
            baker.make(
                WaitingListUser,
                event=self.event,
                user__email="test{}@test.test".format(i),
            )

        # cancel booking
        self.client.login(username=self.user.username, password="test")
        self.client.post(self.url)

        self.event.refresh_from_db()
        # a space left because autobook user was already booked
        self.assertEqual(self.event.spaces_left, 1)

        # autobook user still booked and not on waiting list
        open_booking_emails = self.event.bookings.filter(
            status="OPEN", no_show=False
        ).values_list("user__email", flat=True)
        self.assertTrue("test1@test.test" in open_booking_emails)
        # user removed from waiting list
        self.assertFalse(
            WaitingListUser.objects.filter(user__email="test1@test.test").exists()
        )

        # email to user, studio and 1 to all waiting list emails
        self.assertEqual(len(mail.outbox), 3)
        self.assertEqual(
            [[self.user.email], [settings.DEFAULT_STUDIO_EMAIL], []],
            [mail.to for mail in mail.outbox],
        )
        self.assertIn("space now available", mail.outbox[2].subject)
        self.assertEqual(mail.outbox[2].bcc, ["test2@test.test", "test3@test.test"])

    def test_error_if_outstanding_fees(self):
        baker.make_recipe(
            "booking.booking",
            event__cancellation_fee=1.00,
            user=self.user,
            cancellation_fee_incurred=True,
        )
        self.client.login(username=self.user.username, password="test")
        resp = self.client.post(self.url)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(
            resp.content.decode("utf-8"),
            "Action forbidden until outstanding cancellation fees have been resolved",
        )


class AjaxTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = baker.make_recipe(
            "booking.user", email="test@test.com", password="test"
        )

    def setUp(self):
        super().setUp()
        self.event = baker.make_recipe("booking.future_PC", max_participants=3)
        self.client.force_login(self.user)

    def test_update_bookings_count_spaces(self):
        url = reverse("booking:update_booking_count", args=[self.event.id])
        resp = self.client.get(url)
        self.assertEqual(
            resp.json(),
            {
                "booking_count": "3/3",
                "full": False,
                "booked": False,
                "cart_item_menu_count": 0,
            },
        )

    def test_update_bookings_count_full(self):
        url = reverse("booking:update_booking_count", args=[self.event.id])
        baker.make_recipe("booking.booking", event=self.event, _quantity=3)
        resp = self.client.get(url)
        self.assertEqual(
            resp.json(),
            {
                "booking_count": "0/3",
                "full": True,
                "booked": False,
                "cart_item_menu_count": 0,
            },
        )

    def test_toggle_waiting_list_on(self):
        url = reverse("booking:toggle_waiting_list", args=[self.event.id])
        self.assertFalse(WaitingListUser.objects.exists())
        resp = self.client.post(url)

        wl_user = WaitingListUser.objects.first()
        self.assertEqual(wl_user.user, self.user)
        self.assertEqual(wl_user.event, self.event)

        self.assertEqual(resp.context["event"], self.event)
        self.assertEqual(resp.context["on_waiting_list"], True)

    def test_toggle_waiting_list_off(self):
        url = reverse("booking:toggle_waiting_list", args=[self.event.id])
        baker.make(WaitingListUser, user=self.user, event=self.event)
        resp = self.client.post(url)

        self.assertFalse(WaitingListUser.objects.exists())
        self.assertEqual(resp.context["event"], self.event)
        self.assertEqual(resp.context["on_waiting_list"], False)

    def test_toggle_waiting_error_if_outstanding_fees(self):
        baker.make_recipe(
            "booking.booking",
            event__cancellation_fee=1.00,
            user=self.user,
            cancellation_fee_incurred=True,
        )
        url = reverse("booking:toggle_waiting_list", args=[self.event.id])
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(
            resp.content.decode("utf-8"),
            "Action forbidden until outstanding cancellation fees have been resolved",
        )

    def test_booking_details(self):
        """Return correct details to populate the bookings page"""
        url = reverse("booking:booking_details", args=[self.event.id])
        booking = baker.make_recipe(
            "booking.booking",
            event=self.event,
            user=self.user,
            paid=False,
            status="OPEN",
        )
        resp = self.client.post(url)
        # event has 0 cost, no advance payment required
        self.assertEqual(
            resp.json(),
            {
                "display_status": "OPEN",
                "status": "OPEN",
                "no_show": False,
                "display_paid": '<span class="text-danger fas fa-times-circle"></span>',
                "display_membership": '<span class="text-danger fas fa-times-circle"></span>',
                "cart_item_menu_count": 1,
            },
        )

        self.event.cost = 10
        self.event.save()
        resp = self.client.post(url)
        # event has cost, no advance payment required
        self.assertEqual(
            resp.json(),
            {
                "status": "OPEN",
                "display_status": "OPEN",
                "no_show": False,
                "display_paid": '<span class="text-danger fas fa-times-circle"></span>',
                "display_membership": '<span class="text-danger fas fa-times-circle"></span>',
                "cart_item_menu_count": 1,
            },
        )

        # no show booking
        booking.no_show = True
        booking.save()
        resp = self.client.post(url)
        # event has cost, no advance payment required
        self.assertEqual(
            resp.json(),
            {
                "cart_item_menu_count": 0,
                "status": "OPEN",
                "display_status": "CANCELLED",
                "no_show": True,
                "display_paid": '<span class="text-danger fas fa-times-circle"></span>',
                "display_membership": '<span class="text-danger fas fa-times-circle"></span>',
            },
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
                "cart_item_menu_count": 0,
                "status": "OPEN",
                "display_status": "OPEN",
                "no_show": False,
                "display_paid": '<span class="text-success fas fa-check-circle"></span>',
                "display_membership": '<span class="text-danger fas fa-times-circle"></span>',
            },
        )


class AjaxCartItemDeleteView(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = baker.make_recipe(
            "booking.user", email="test@test.com", password="test"
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_delete_booking(self):
        booking = baker.make_recipe(
            "booking.booking",
            event__date=timezone.now() + timedelta(days=1),
            user=self.user,
        )
        booking1 = baker.make_recipe(
            "booking.booking",
            event__date=timezone.now() + timedelta(days=1),
            user=self.user,
            event__cost=5,
        )
        url = reverse("booking:ajax_cart_item_delete")
        resp = self.client.post(
            url, {"item_type": "booking", "item_id": booking.id}
        ).json()
        assert Booking.objects.count() == 1
        assert resp["cart_total"] == "5.00"
        assert resp["cart_item_menu_count"] == 1

        # delete booking1 - no bookings now in cart, redirects to refresh page
        resp = self.client.post(
            url, {"item_type": "booking", "item_id": booking1.id}
        ).json()
        assert not Booking.objects.exists()
        assert resp["redirect"]

    def test_delete_membership(self):
        membership = baker.make_recipe("booking.membership", user=self.user)
        # second membership in cart so we don't redirect
        baker.make_recipe(
            "booking.membership", membership_type__cost=25, user=self.user
        )
        url = reverse("booking:ajax_cart_item_delete")
        resp = self.client.post(
            url, {"item_type": "membership", "item_id": membership.id}
        ).json()
        assert Membership.objects.count() == 1
        assert resp["cart_total"] == "25.00"
        assert resp["cart_item_menu_count"] == 1

    def test_recalculate_total_cart_items(self):
        # calculate total for all items
        # the booking to delete
        booking = baker.make_recipe(
            "booking.booking",
            event__cost=10,
            user=self.user,
            event__date=timezone.now() + timedelta(days=1),
        )
        # another booking and membership
        baker.make_recipe(
            "booking.booking",
            event__cost=12,
            user=self.user,
            event__date=timezone.now() + timedelta(days=1),
        )
        baker.make_recipe(
            "booking.membership", membership_type__cost=20, user=self.user
        )
        # some bookings for another user
        baker.make_recipe("booking.booking", _quantity=2)
        # paid bookings don't count towards total
        baker.make_recipe("booking.booking", user=self.user, paid=True)

        url = reverse("booking:ajax_cart_item_delete")
        resp = self.client.post(
            url, {"item_type": "booking", "item_id": booking.id}
        ).json()

        # 2 items still in cart - not the deleted one or the paid ones
        assert resp["cart_total"] == "32.00"
        assert resp["cart_item_menu_count"] == 2

    def test_delete_booking_event_with_waiting_list(self):
        event = baker.make_recipe("booking.future_PC")
        booking = baker.make_recipe("booking.booking", user=self.user, event=event)
        baker.make(WaitingListUser, user__email="waiting@test.com", event=event)
        url = reverse("booking:ajax_cart_item_delete")
        self.client.post(url, {"item_type": "booking", "item_id": booking.id}).json()

        assert len(mail.outbox) == 1
        assert mail.outbox[0].bcc == ["waiting@test.com"]

    def test_delete_gift_voucher(self):
        gift_voucher = baker.make_recipe(
            "booking.gift_voucher_10",
            total_voucher__purchaser_email=self.user.email,
        )
        # second gift_voucher in cart so we don't redirect
        gift_voucher1 = baker.make_recipe(
            "booking.gift_voucher_11",
            total_voucher__purchaser_email=self.user.email,
        )
        url = reverse("booking:ajax_cart_item_delete")
        resp = self.client.post(
            url, {"item_type": "gift_voucher", "item_id": gift_voucher.id}
        ).json()
        assert GiftVoucher.objects.count() == 1
        assert resp["cart_total"] == "11.00"
        assert resp["cart_item_menu_count"] == 1

        # delete the second one
        resp = self.client.post(
            url, {"item_type": "gift_voucher", "item_id": gift_voucher1.id}
        ).json()
        assert not GiftVoucher.objects.exists()
        assert resp["redirect"]

    def test_delete_gift_voucher_anonymous_user(self):
        self.client.logout()
        gift_voucher = baker.make_recipe(
            "booking.gift_voucher_10",
            total_voucher__purchaser_email="anon@test.com",
        )
        # second gift_voucher in cart so we don't redirect
        gift_voucher1 = baker.make_recipe(
            "booking.gift_voucher_11",
            total_voucher__purchaser_email="anon@test.com",
        )
        session = self.client.session
        session.update(
            {"purchases": {"gift_vouchers": [gift_voucher.id, gift_voucher1.id]}}
        )
        session.save()

        url = reverse("booking:ajax_cart_item_delete")
        resp = self.client.post(
            url, {"item_type": "gift_voucher", "item_id": gift_voucher.id}
        ).json()
        assert GiftVoucher.objects.count() == 1
        assert resp["cart_total"] == "11.00"
        assert resp["cart_item_menu_count"] == 1

        # delete the second one
        resp = self.client.post(
            url, {"item_type": "gift_voucher", "item_id": gift_voucher1.id}
        ).json()
        assert not GiftVoucher.objects.exists()
        assert resp["redirect"]

        # cart items in context have been updated also
        resp = self.client.get(reverse("booking:guest_shopping_basket"))
        assert resp.context_data["unpaid_gift_voucher_info"] == []
