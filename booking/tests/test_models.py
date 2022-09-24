# -*- coding: utf-8 -*-
from collections import UserDict
from datetime import timedelta, datetime
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from django.urls import reverse

import pytest

from model_bakery import baker

from booking.models import Event, Booking, ItemVoucher, Membership, MembershipType, TotalVoucher
from stripe_payments.models import Invoice

now = timezone.now()


class EventTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.event = baker.make_recipe('booking.future_EV')

    def test_bookable_spaces(self):
        event = baker.make_recipe('booking.future_EV', max_participants=2)
        self.assertTrue(event.bookable)

        baker.make_recipe('booking.booking', event=event, _quantity=2)
        # need to get event again as bookable is cached property
        event = Event.objects.get(id=event.id)
        self.assertFalse(event.bookable)

    def test_str(self):
        event = baker.make_recipe(
            'booking.past_event',
            name='Test event',
            date=datetime(2015, 1, 1, tzinfo=timezone.utc)
        )
        self.assertEqual(str(event), 'Test event - 01 Jan 2015, 00:00')


class BookingTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.event = baker.make_recipe('booking.future_EV', max_participants=20)
        cls.event_no_cost = baker.make_recipe(
            'booking.future_PC', cost=0, date=datetime(2020, 2, 10, 18, 0, tzinfo=timezone.utc)
        )

    def setUp(self):
        baker.make_recipe('booking.user', _quantity=15)
        self.users = User.objects.all()
        self.event_with_cost = baker.make_recipe('booking.future_EV')

    def test_event_spaces_left(self):
        """
        Test that spaces left is calculated correctly
        """

        self.assertEqual(self.event.max_participants, 20)
        self.assertEqual(self.event.spaces_left, 20)

        for user in self.users:
            baker.make_recipe('booking.booking', user=user, event=self.event)

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
            baker.make_recipe('booking.booking', user=user, event=self.event)
        baker.make_recipe(
            'booking.booking', event=self.event, no_show=True
        )
        baker.make_recipe(
            'booking.booking', event=self.event, status='CANCELLED'
        )
        # 20 total spaces, 15 open bookings, 1 cancelled, 1 no-show; still 5
        # spaces left
        # we need to get the event again as spaces_left is cached property
        event = Event.objects.get(id=self.event.id)
        self.assertEqual(event.bookings.count(), 17)
        self.assertEqual(event.spaces_left, 5)

    def test_str(self):
        booking = baker.make_recipe(
            'booking.booking',
            event=baker.make_recipe('booking.future_EV', name='Test event'),
            user=baker.make_recipe('booking.user', username='Test user'),
            )
        self.assertEqual(str(booking), 'Test event - Test user')

    def test_booking_full_event(self):
        """
        Test that attempting to create new booking for full event raises
        ValidationError
        """
        self.event_with_cost.max_participants = 3
        self.event_with_cost.save()
        baker.make_recipe(
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
        baker.make_recipe(
            'booking.booking', event=self.event_with_cost, _quantity=3
        )
        event = Event.objects.get(id=self.event_with_cost.id)
        booking = baker.make_recipe(
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
        baker.make_recipe(
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
        booking = baker.make_recipe(
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
        booking = baker.make_recipe(
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
        baker.make_recipe(
            'booking.booking', event=self.event_with_cost, _quantity=3
        )
        event = Event.objects.get(id=self.event_with_cost.id)
        booking = baker.make_recipe(
            'booking.booking', event=event, user=user, status='CANCELLED'
        )
        with self.assertRaises(ValidationError):
            booking.status = 'OPEN'
            booking.save()

        booking.refresh_from_db()
        self.assertIsNone(booking.date_rebooked)

    def test_booking_cannot_be_no_show_and_attended(self):
        booking = baker.make_recipe('booking.booking', event=self.event)
        booking.attended = True
        booking.no_show = True
        with self.assertRaises(ValidationError):
            booking.save()

    @patch('booking.models.timezone')
    def test_cancel_booking_within_cancellation_period(self, mock_tz):
        # event_no_cost date 2020-2-10 18:00
        # < 24hrs before event date
        mock_tz.now.return_value = datetime(2020, 2, 9, 20, 0, tzinfo=timezone.utc)
        booking = baker.make_recipe('booking.booking', event=self.event_no_cost, status="OPEN", paid=False)
        self.assertFalse(booking.cancellation_fee_incurred)
        self.assertFalse(booking.cancellation_fee_paid)
        booking.status = "CANCELLED"
        booking.save()
        self.assertTrue(booking.cancellation_fee_incurred)
        self.assertFalse(booking.cancellation_fee_paid)

    @patch('booking.models.timezone')
    def test_set_to_no_show_within_cancellation_period(self, mock_tz):
        # event_no_cost date 2020-2-10 18:00
        # < 24hrs before event date
        mock_tz.now.return_value = datetime(2020, 2, 9, 20, 0, tzinfo=timezone.utc)
        booking = baker.make_recipe('booking.booking', event=self.event_no_cost, status="OPEN", paid=False)
        self.assertFalse(booking.cancellation_fee_incurred)
        self.assertFalse(booking.cancellation_fee_paid)
        booking.no_show = True
        booking.save()
        self.assertEqual(booking.status, "OPEN")
        self.assertTrue(booking.cancellation_fee_incurred)
        self.assertFalse(booking.cancellation_fee_paid)

    @patch('booking.models.timezone')
    def test_no_cancellation_fees_if_event_cancelled(self, mock_tz):
        cancelled_event = baker.make_recipe(
            'booking.future_PC', cost=0, date=datetime(2020, 2, 10, 18, 0, tzinfo=timezone.utc)
        )
        # < 24hrs before event date
        mock_tz.now.return_value = datetime(2020, 2, 9, 20, 0, tzinfo=timezone.utc)
        booking = baker.make_recipe('booking.booking', event=cancelled_event, status="OPEN", paid=False)
        cancelled_event.cancelled = True
        cancelled_event.save()

        self.assertFalse(booking.cancellation_fee_incurred)
        self.assertFalse(booking.cancellation_fee_paid)
        booking.status = "CANCELLED"
        booking.save()
        self.assertFalse(booking.cancellation_fee_incurred)
        self.assertFalse(booking.cancellation_fee_paid)

    @patch('booking.models.timezone')
    def test_no_cancellation_fee_incurred_if_event_cancellation_fee_is_0(self, mock_tz):
        cancelled_event = baker.make_recipe(
            'booking.future_PC', cost=0, date=datetime(2020, 2, 10, 18, 0, tzinfo=timezone.utc),
            cancellation_fee=0
        )
        # < 24hrs before event date
        mock_tz.now.return_value = datetime(2020, 2, 9, 20, 0, tzinfo=timezone.utc)
        booking = baker.make_recipe('booking.booking', event=cancelled_event, status="OPEN", paid=False)

        self.assertFalse(booking.cancellation_fee_incurred)
        self.assertFalse(booking.cancellation_fee_paid)
        booking.status = "CANCELLED"
        booking.save()
        self.assertFalse(booking.cancellation_fee_incurred)
        self.assertFalse(booking.cancellation_fee_paid)

    def test_rebooking_resets_cancellation_fee_flags(self):
        booking = baker.make_recipe(
            'booking.booking', event=self.event_no_cost, status="CANCELLED", paid=False,
            cancellation_fee_incurred=True, cancellation_fee_paid=True
        )
        self.assertTrue(booking.cancellation_fee_incurred)
        self.assertTrue(booking.cancellation_fee_paid)
        booking.status = "OPEN"
        booking.save()
        self.assertFalse(booking.cancellation_fee_incurred)
        self.assertFalse(booking.cancellation_fee_paid)

    def test_resetting_no_show_resets_cancellation_fee_flags(self):
        booking = baker.make_recipe(
            'booking.booking', event=self.event_no_cost, status="OPEN", paid=False, no_show=True,
            cancellation_fee_incurred=True, cancellation_fee_paid=False
        )
        self.assertTrue(booking.cancellation_fee_incurred)
        booking.no_show = False
        booking.save()
        self.assertFalse(booking.cancellation_fee_incurred)
        self.assertFalse(booking.cancellation_fee_paid)


@pytest.mark.django_db 
def test_membership_type_model():
    membership_type = baker.make(
        MembershipType, name="test", cost=10, number_of_classes=4
    )
    assert str(membership_type) == "test - £10"


@pytest.mark.django_db 
def test_item_voucher_validation():
    with pytest.raises(ValidationError):
        # no discount or discount amount
        baker.make(ItemVoucher, code="test")

    with pytest.raises(ValidationError):
        # no discount or discount amount
        baker.make(ItemVoucher, code="test", discount=10, discount_amount=10)
    
    voucher = baker.make(ItemVoucher, code="test", discount=10)
    assert str(voucher) == "test - 10%"

    voucher = baker.make(ItemVoucher, code="test1", discount_amount=10)
    assert str(voucher) == "test1 - £10"


@pytest.mark.django_db 
def test_item_voucher_generate_code():
    voucher = baker.make(ItemVoucher, discount=10, code=None)
    assert len(voucher.code) == 12


@pytest.mark.django_db 
@patch("booking.models.ItemVoucher._generate_code")
def test_item_voucher_generate_code_duplicates(mock_generate_code):
    mock_generate_code.side_effect = ["123", "123", "234"]
    voucher = baker.make(ItemVoucher, discount=10, code=None)
    assert voucher.code == "123"

    voucher = baker.make(ItemVoucher, discount=10, code=None)
    assert voucher.code == "234"


@pytest.mark.django_db 
def test_item_voucher_valid_for():
    membership_type = baker.make(
        MembershipType, name="test", cost=10, number_of_classes=4
    )
    voucher = baker.make(ItemVoucher, discount=10, event_types=["private"])
    voucher.membership_types.add(membership_type)

    assert voucher.valid_for() == ["test (membership)", "private"]


@pytest.mark.django_db 
def test_item_voucher_uses():
    membership_type = baker.make(
        MembershipType, name="test", cost=10, number_of_classes=4
    )
    voucher = baker.make(ItemVoucher, discount=10, event_types=["private"])
    voucher.membership_types.add(membership_type)

    baker.make(Membership, voucher=voucher, paid=True, _quantity=3)
    baker.make(Booking, voucher=voucher, paid=True, _quantity=3)
    baker.make(Booking, voucher=voucher, paid=False, _quantity=3)
    baker.make(Booking, paid=True, _quantity=2)

    assert voucher.uses() == 6

    user = baker.make(User)
    booking = Booking.objects.first()
    membership = Membership.objects.first()
    for item in [booking, membership]:
        item.user = user
        item.save()
    assert voucher.uses(user) == 2


@pytest.mark.django_db 
def test_total_voucher_uses():
    voucher = baker.make(TotalVoucher, code="test", discount=10)
    baker.make(Invoice, total_voucher_code="test", _quantity=3, paid=True)
    baker.make(Invoice, _quantity=3, paid=True)

    assert voucher.uses() == 3