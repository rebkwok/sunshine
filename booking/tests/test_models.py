# -*- coding: utf-8 -*-
from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from django.core.urlresolvers import reverse

from datetime import timedelta, datetime
from unittest.mock import patch
from model_mommy import mommy

from booking.models import Event, Booking

now = timezone.now()


class EventTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.event = mommy.make_recipe('booking.future_EV')

    def test_bookable_spaces(self):
        event = mommy.make_recipe('booking.future_EV', max_participants=2)
        self.assertTrue(event.bookable)

        mommy.make_recipe('booking.booking', event=event, _quantity=2)
        # need to get event again as bookable is cached property
        event = Event.objects.get(id=event.id)
        self.assertFalse(event.bookable)

    def test_absolute_url(self):
        self.assertEqual(
            self.event.get_absolute_url(),
            reverse('booking:event_detail', kwargs={'slug': self.event.slug})
        )

    def test_str(self):
        event = mommy.make_recipe(
            'booking.past_event',
            name='Test event',
            date=datetime(2015, 1, 1, tzinfo=timezone.utc)
        )
        self.assertEqual(str(event), 'Test event - 01 Jan 2015, 00:00')


class BookingTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.event = mommy.make_recipe('booking.future_EV', max_participants=20)

    def setUp(self):
        mommy.make_recipe('booking.user', _quantity=15)
        self.users = User.objects.all()
        self.event_with_cost = mommy.make_recipe('booking.future_EV')

    def test_event_spaces_left(self):
        """
        Test that spaces left is calculated correctly
        """

        self.assertEqual(self.event.max_participants, 20)
        self.assertEqual(self.event.spaces_left, 20)

        for user in self.users:
            mommy.make_recipe('booking.booking', user=user, event=self.event)

        # we need to get the event again as spaces_left is cached property
        event = Event.objects.get(id=self.event.id)
        self.assertEqual(event.spaces_left, 5)

    def test_event_spaces_left_does_not_count_cancelled_or_no_shows(self):
        """
        Test that spaces left is calculated correctly
        """

        self.assertEqual(self.event.max_participants, 20)
        self.assertEqual(self.event.spaces_left, 20)

        for user in self.users:
            mommy.make_recipe('booking.booking', user=user, event=self.event)
        mommy.make_recipe(
            'booking.booking', event=self.event, no_show=True
        )
        mommy.make_recipe(
            'booking.booking', event=self.event, status='CANCELLED'
        )
        # 20 total spaces, 15 open bookings, 1 cancelled, 1 no-show; still 5
        # spaces left
        # we need to get the event again as spaces_left is cached property
        event = Event.objects.get(id=self.event.id)
        self.assertEqual(event.bookings.count(), 17)
        self.assertEqual(event.spaces_left, 5)

    def test_str(self):
        booking = mommy.make_recipe(
            'booking.booking',
            event=mommy.make_recipe('booking.future_EV', name='Test event'),
            user=mommy.make_recipe('booking.user', username='Test user'),
            )
        self.assertEqual(str(booking), 'Test event - Test user')

    def test_booking_full_event(self):
        """
        Test that attempting to create new booking for full event raises
        ValidationError
        """
        self.event_with_cost.max_participants = 3
        self.event_with_cost.save()
        mommy.make_recipe(
            'booking.booking', event=self.event_with_cost, _quantity=3
        )
        # we need to get the event again as spaces_left is cached property
        event = Event.objects.get(id=self.event_with_cost.id)
        with self.assertRaises(ValidationError):
            Booking.objects.create(
                event=event, user=self.users[0]
            )

    def test_reopening_booking_full_event(self):
        """
        Test that attempting to reopen a cancelled booking for now full event
        raises ValidationError
        """
        self.event_with_cost.max_participants = 3
        self.event_with_cost.save()
        user = self.users[0]
        mommy.make_recipe(
            'booking.booking', event=self.event_with_cost, _quantity=3
        )
        event = Event.objects.get(id=self.event_with_cost.id)
        booking = mommy.make_recipe(
            'booking.booking', event=event, user=user, status='CANCELLED'
        )
        with self.assertRaises(ValidationError):
            booking.status = 'OPEN'
            booking.save()

    def test_can_create_cancelled_booking_for_full_event(self):
        """
        Test that attempting to create new cancelled booking for full event
        does not raise error
        """
        self.event_with_cost.max_participants = 3
        self.event_with_cost.save()
        mommy.make_recipe(
            'booking.booking', event=self.event_with_cost, _quantity=3
        )
        Booking.objects.create(
            event=self.event_with_cost, user=self.users[0], status='CANCELLED'
        )
        self.assertEqual(
            Booking.objects.filter(event=self.event_with_cost).count(), 4
        )

    @patch('booking.models.timezone')
    def test_reopening_booking_sets_date_reopened(self, mock_tz):
        """
        Test that reopening a cancelled booking for an event with spaces sets
        the rebooking date
        """
        mock_now = datetime(2015, 1, 1, tzinfo=timezone.utc)
        mock_tz.now.return_value = mock_now
        user = self.users[0]
        booking = mommy.make_recipe(
            'booking.booking', event=self.event_with_cost, user=user,
            status='CANCELLED'
        )

        self.assertIsNone(booking.date_rebooked)
        booking.status = 'OPEN'
        booking.save()
        booking.refresh_from_db()
        self.assertEqual(booking.date_rebooked, mock_now)


    @patch('booking.models.timezone')
    def test_reopening_booking_again_resets_date_reopened(self, mock_tz):
        """
        Test that reopening a second time resets the rebooking date
        """
        mock_now = datetime(2015, 3, 1, tzinfo=timezone.utc)
        mock_tz.now.return_value = mock_now
        user = self.users[0]
        booking = mommy.make_recipe(
            'booking.booking', event=self.event_with_cost, user=user,
            status='CANCELLED',
            date_rebooked=datetime(2015, 1, 1, tzinfo=timezone.utc)
        )
        self.assertEqual(
            booking.date_rebooked, datetime(2015, 1, 1, tzinfo=timezone.utc)
        )
        booking.status = 'OPEN'
        booking.save()
        booking.refresh_from_db()
        self.assertEqual(booking.date_rebooked, mock_now)

    def test_reopening_booking_full_event_does_not_set_date_reopened(self):
        """
        Test that attempting to reopen a cancelled booking for now full event
        raises ValidationError and does not set date_reopened
        """
        self.event_with_cost.max_participants = 3
        self.event_with_cost.save()
        user = self.users[0]
        mommy.make_recipe(
            'booking.booking', event=self.event_with_cost, _quantity=3
        )
        event = Event.objects.get(id=self.event_with_cost.id)
        booking = mommy.make_recipe(
            'booking.booking', event=event, user=user, status='CANCELLED'
        )
        with self.assertRaises(ValidationError):
            booking.status = 'OPEN'
            booking.save()

        booking.refresh_from_db()
        self.assertIsNone(booking.date_rebooked)
