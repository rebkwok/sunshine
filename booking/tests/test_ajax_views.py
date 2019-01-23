# -*- coding: utf-8 -*-
from datetime import datetime
from unittest.mock import patch
from model_mommy import mommy

from django.conf import settings
from django.core import mail
from django.urls import reverse
from django.test import override_settings, TestCase
from django.contrib.auth.models import Group, User
from django.utils import timezone

from accounts.tests import make_data_privacy_agreement

from ..models import Event, Booking, WaitingListUser
from .helpers import TestSetupMixin


class BookingToggleAjaxCreateViewTests(TestSetupMixin, TestCase):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.event = mommy.make_recipe(
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
        event = mommy.make_recipe(
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
        users = mommy.make_recipe('booking.user', _quantity=3)
        for user in users:
            mommy.make_recipe('booking.booking', event=self.event, user=user)
        # check event is full; we need to get the event again as spaces_left is
        # cached property
        event = Event.objects.get(id=self.event.id)
        self.assertEqual(event.spaces_left, 0)

        self.client.login(username=self.user.username, password='test')
        # try to book for event
        resp = self.client.post(self.url)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.content.decode('utf-8'), 'Sorry, this event is now full')

    def test_cannot_book_for_cancelled_event(self):
        """cannot create booking for a full event
        """
        event = mommy.make_recipe('booking.future_EV', max_participants=3, cancelled=True, cost=5)
        url = reverse('booking:toggle_booking', args=[event.id])

        self.client.login(username=self.user.username, password='test')
        # try to book for event
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.content.decode('utf-8'), 'Sorry, this event has been cancelled')

    def test_cancelled_booking_can_be_rebooked(self):
        """
        Test can load create booking page with a cancelled booking
        """
        booking = mommy.make_recipe(
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
        pclass = mommy.make_recipe(
            'booking.future_PC', allow_booking_cancellation=False, cost=10
        )
        url = reverse('booking:toggle_booking', args=[pclass.id])

        # book for non-refundable event and mark as no_show
        booking = mommy.make_recipe(
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
        mommy.make(WaitingListUser, event=self.event, user=self.user)
        mommy.make(WaitingListUser, event=self.event)
        mommy.make(WaitingListUser, user=self.user)
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
        booking = mommy.make_recipe('booking.booking', user=self.user, event=self.event)
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
        event = mommy.make_recipe('booking.future_PC', date=datetime(2018, 1, 1, 10, tzinfo=timezone.utc))
        url = reverse('booking:toggle_booking', args=[event.id])

        booking = mommy.make_recipe('booking.booking', user=self.user, event=event)
        self.client.login(username=self.user.username, password='test')
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp.context['alert_message']['message'], 'Cancelled.'
        )
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'OPEN')
        self.assertTrue(booking.no_show)

    def test_cancel_full_booking_emails_waiting_list(self):
        """
        Toggle booking to cancelled
        """
        booking = mommy.make_recipe('booking.booking', user=self.user, event=self.event)
        mommy.make_recipe('booking.booking', event=self.event, _quantity=2)
        for i in range(3):
            mommy.make(WaitingListUser, event=self.event, user__email='test{}@test.test'.format(i))

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


class AjaxTests(TestSetupMixin, TestCase):

    def setUp(self):
        super().setUp()
        self.event = mommy.make_recipe('booking.future_PC', max_participants=3)
        self.client.login(username=self.user.username, password='test')

    def test_update_bookings_count_spaces(self):
        url = reverse('booking:update_booking_count', args=[self.event.id])
        resp = self.client.get(url)
        self.assertEqual(resp.json(), {'booking_count': '3/3', 'full': False, 'booked': False})

    def test_update_bookings_count_full(self):
        url = reverse('booking:update_booking_count', args=[self.event.id])
        mommy.make_recipe('booking.booking', event=self.event, _quantity=3)
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
        mommy.make(WaitingListUser, user=self.user, event=self.event)
        resp = self.client.post(url)

        self.assertFalse(WaitingListUser.objects.exists())
        self.assertEqual(resp.context['event'], self.event)
        self.assertEqual(resp.context['on_waiting_list'], False)

    def test_booking_details(self):
        """Return correct details to populate the bookings page"""
        url = reverse('booking:booking_details', args=[self.event.id])
        booking = mommy.make_recipe(
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
                'display_paid': '<span class="fas fa-times"></span>',
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
                'display_paid': '<span class="fas fa-times"></span>',
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
                'display_paid': '<span class="fas fa-times"></span>',
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
                'display_paid': '<span class="fas fa-check"></span>',
            }
        )
