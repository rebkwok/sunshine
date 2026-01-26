# -*- coding: utf-8 -*-
from datetime import timedelta, datetime
from datetime import timezone as dt_timezone

from unittest.mock import patch

from dateutil.relativedelta import relativedelta

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

import pytest

from model_bakery import baker

from booking.models import Event, Booking, GiftVoucher, GiftVoucherType, ItemVoucher, Membership, MembershipType, TotalVoucher
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
            date=datetime(2015, 1, 1, tzinfo=dt_timezone.utc)
        )
        self.assertEqual(str(event), 'Test event - 01 Jan 2015, 00:00')


@pytest.mark.django_db
@pytest.mark.parametrize(
    "now,event_date,can_cancel,cancellation_period",
    [
        # now = DST, event = not DST
        # Although there are only 23 hrs between now and the event datetime, cancellation
        # is allowed because it crosses DST
        # i.e. in local time, it's currently 9.30am, and the event start is 10am, so users
        # expect to be able to cancel
        (
            datetime(2023, 3, 25, 9, 30, tzinfo=dt_timezone.utc), # not DST
            datetime(2023, 3, 26, 9, 0, tzinfo=dt_timezone.utc), # DST
            True,
            24
        ),
        # This is > 24 hrs
        (
            datetime(2023, 3, 25, 8, 30, tzinfo=dt_timezone.utc), # not DST
            datetime(2023, 3, 26, 9, 0, tzinfo=dt_timezone.utc), # DST
            True,
            24
        ),
        # less than 23 hrs
        (
            datetime(2023, 3, 25, 10, 5, tzinfo=dt_timezone.utc), # not DST
            datetime(2023, 3, 26, 9, 0, tzinfo=dt_timezone.utc), # DST
            False,
            24
        ),
        # both DST, <24 hrs
        (
            datetime(2023, 3, 26, 9, 30, tzinfo=dt_timezone.utc),
            datetime(2023, 3, 27, 9, 0, tzinfo=dt_timezone.utc),
            False,
            24
        ),
        # longer cancellation period
        (
            datetime(2023, 3, 23, 9, 30, tzinfo=dt_timezone.utc), # not DST
            datetime(2023, 3, 26, 9, 0, tzinfo=dt_timezone.utc), # DST
            True,
            72
        ),
        # longer cancellation period
        (
            datetime(2023, 3, 23, 8, 30, tzinfo=dt_timezone.utc), # not DST
            datetime(2023, 3, 26, 9, 0, tzinfo=dt_timezone.utc), # DST
            True,
            72
        ),
        # longer cancellation period
        (
            datetime(2023, 3, 23, 10, 30, tzinfo=dt_timezone.utc), # not DST
            datetime(2023, 3, 26, 9, 0, tzinfo=dt_timezone.utc), # DST
            False,
            72
        ),
        # now is DST, event not DST
        # > 24.5 hrs between now and event date
        (
            datetime(2022, 10, 29, 9, 30, tzinfo=dt_timezone.utc), # DST; 10:30 local
            datetime(2022, 10, 30, 10, 0, tzinfo=dt_timezone.utc), # not DST
            False,
            24
        ),
        (
            datetime(2022, 10, 29, 8, 55, tzinfo=dt_timezone.utc), # DST; 10:30 local
            datetime(2022, 10, 30, 10, 0, tzinfo=dt_timezone.utc), # not DST
            True,
            24
        ),
    ]
)
@patch('booking.models.timezone')
def test_can_cancel_with_daylight_savings_time(mock_tz, now, event_date, can_cancel, cancellation_period):
    mock_tz.now.return_value = now
    event = baker.make_recipe(
        'booking.future_EV',
        date=event_date,
        cancellation_period=cancellation_period
    )
    assert event.can_cancel() == can_cancel


class BookingTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.event = baker.make_recipe('booking.future_EV', max_participants=20)
        cls.event_no_cost = baker.make_recipe(
            'booking.future_PC', cost=0, date=datetime(2020, 2, 10, 18, 0, tzinfo=dt_timezone.utc)
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
        mock_now = datetime(2015, 1, 1, tzinfo=dt_timezone.utc)
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
        mock_now = datetime(2015, 3, 1, tzinfo=dt_timezone.utc)
        mock_tz.now.return_value = mock_now
        user = self.users[0]
        booking = baker.make_recipe(
            'booking.booking', event=self.event_with_cost, user=user,
            status='CANCELLED',
            date_rebooked=datetime(2015, 1, 1, tzinfo=dt_timezone.utc)
        )
        self.assertEqual(
            booking.date_rebooked, datetime(2015, 1, 1, tzinfo=dt_timezone.utc)
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
        # < 12hrs before event date
        mock_tz.now.return_value = datetime(2020, 2, 10, 7, 0, tzinfo=dt_timezone.utc)
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
        mock_tz.now.return_value = datetime(2020, 2, 10, 7, 0, tzinfo=dt_timezone.utc)
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
            'booking.future_PC', cost=0, date=datetime(2020, 2, 10, 18, 0, tzinfo=dt_timezone.utc)
        )
        # < 24hrs before event date
        mock_tz.now.return_value = datetime(2020, 2, 9, 20, 0, tzinfo=dt_timezone.utc)
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
            'booking.future_PC', cost=0, date=datetime(2020, 2, 10, 18, 0, tzinfo=dt_timezone.utc),
            cancellation_fee=0
        )
        # < 24hrs before event date
        mock_tz.now.return_value = datetime(2020, 2, 9, 20, 0, tzinfo=dt_timezone.utc)
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
    assert str(membership_type) == "test - £10.00"


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
    assert str(voucher) == "test1 - £10.00"


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

    assert voucher.valid_for() == ["Membership - test", "Private Lesson booking"]


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


@pytest.mark.django_db 
def test_membership(membership_type):
    now = timezone.now()
    future = now + timedelta(days=60)
    past_membership = baker.make(Membership, membership_type=membership_type, month=2, year=2022)
    current_membership = baker.make(Membership, membership_type=membership_type, month=now.month, year=now.year)
    future_membership = baker.make(Membership, membership_type=membership_type, month=future.month, year=future.year)
    
    assert str(past_membership) == "test - February 2022"
    assert past_membership.str_with_abbreviated_month() ==  "test - Feb 2022"
    assert past_membership.start_date() == datetime(2022, 2, 1, tzinfo=dt_timezone.utc)
    assert past_membership.expiry_date() == datetime(2022, 2, 28, tzinfo=dt_timezone.utc)
    assert past_membership.month_str == "February"
    assert not past_membership.current_or_future()
    assert current_membership.current_or_future()
    assert future_membership.current_or_future()
    assert past_membership.has_expired()
    assert not current_membership.has_expired()
    assert not future_membership.has_expired()
    assert not past_membership.full()


@pytest.mark.django_db 
def test_membership_uses(membership_type):
    now = timezone.now()
    current_membership = baker.make(Membership, membership_type=membership_type, month=now.month, year=now.year)
    assert not current_membership.full()
    assert current_membership.current_or_future()

    baker.make(Booking, membership=current_membership, _quantity=2)
    current_membership.refresh_from_db()
    assert current_membership.full()
    assert not current_membership.current_or_future()
    assert current_membership.times_used() == 2


@pytest.mark.django_db 
def test_membership_with_voucher(membership_type):
    now = timezone.now()
    voucher = baker.make(ItemVoucher, discount=50)
    current_membership = baker.make(
        Membership, membership_type=membership_type, month=now.month, year=now.year
    )
    assert current_membership.cost_with_voucher == 20
    current_membership.voucher = voucher
    current_membership.save()
    assert current_membership.cost_with_voucher == 10

    voucher = baker.make(ItemVoucher, discount_amount=10)
    current_membership.voucher = voucher
    current_membership.save()
    assert current_membership.cost_with_voucher == 10
    voucher.discount_amount = 50
    voucher.save()
    assert current_membership.cost_with_voucher == 0


@pytest.mark.django_db 
def test_booking_with_voucher():
    voucher = baker.make(ItemVoucher, discount=50)
    booking = baker.make(Booking, event__cost=10)
    assert booking.cost_with_voucher == 10
    booking.voucher = voucher
    booking.save()
    assert booking.cost_with_voucher == 5

    voucher = baker.make(ItemVoucher, discount_amount=8)
    booking.voucher = voucher
    booking.save()
    assert booking.cost_with_voucher == 2
    voucher.discount_amount = 50
    voucher.save()
    assert booking.cost_with_voucher == 0


@pytest.mark.django_db 
def test_gift_voucher_type_item_type_or_discount_required(membership_type):
    with pytest.raises(
        ValidationError, 
        match="One of event type, membership, or a fixed voucher value is required"
    ):
        GiftVoucherType.objects.create()

    with pytest.raises(
        ValidationError, 
        match="Select ONLY ONE of event type, membership or a fixed voucher value"
    ):
        GiftVoucherType.objects.create(
            membership_type=membership_type, discount_amount=10
        )

    with pytest.raises(
        ValidationError, 
        match="Select ONLY ONE of event type, membership or a fixed voucher value"
    ):
        GiftVoucherType.objects.create(
            membership_type=membership_type, discount_amount=10, event_type="regular_sessions"
        )
    GiftVoucherType.objects.create(membership_type=membership_type)
    GiftVoucherType.objects.create(event_type="regular_session")
    GiftVoucherType.objects.create(discount_amount=10)


@pytest.mark.django_db 
def test_gift_voucher_type_unique_validation(membership_type):
    GiftVoucherType.objects.create(membership_type=membership_type)
    with pytest.raises(ValidationError, match="already exists"):
        GiftVoucherType.objects.create(membership_type=membership_type)

    GiftVoucherType.objects.create(event_type="regular_session")
    with pytest.raises(ValidationError, match="already exists"):
        GiftVoucherType.objects.create(event_type="regular_session")

    GiftVoucherType.objects.create(discount_amount=10)
    with pytest.raises(ValidationError, match="already exists"):
        GiftVoucherType.objects.create(discount_amount=10)

    GiftVoucherType.objects.create(event_type="private")
    GiftVoucherType.objects.create(discount_amount=5)


@pytest.mark.django_db 
@pytest.mark.parametrize(
    "kwargs,expected",
    [
        ({"membership_type": ""}, 20),
        ({"event_type": "regular_session"}, 15),
        ({"event_type": "workshop"}, 15),
        ({"event_type": "private"}, 15),
        ({"discount_amount": 25}, 25)
    ]
)
def test_gift_voucher_type_cost(membership_type, kwargs, expected):
    if "event_type" in kwargs:
        baker.make(Event, event_type=kwargs["event_type"], cost=15)
    elif "membership_type" in kwargs:
        kwargs["membership_type"] = membership_type
    gift_voucher_type = GiftVoucherType.objects.create(**kwargs)
    assert gift_voucher_type.cost == expected


@pytest.mark.django_db 
def test_gift_voucher_type_str(gift_voucher_types):
    baker.make(Event, event_type="private", cost=15)
    baker.make(Event, event_type="regular_session", cost=10)

    assert str(gift_voucher_types["private"]) == "Private Lesson - £15.00"
    assert str(gift_voucher_types["regular_session"]) == "Class - £10.00"
    assert str(gift_voucher_types["total"]) == "Voucher - £10.00"
    assert str(gift_voucher_types["membership_2"]) == "Membership - test - £20.00"
    assert str(gift_voucher_types["membership_4"]) == "Membership - test4 - £40.00"


@pytest.mark.django_db 
def test_gift_voucher_properties(gift_voucher_types):
    gift_voucher = baker.make(
        GiftVoucher, 
        gift_voucher_type=gift_voucher_types["regular_session"],
    )
    voucher = gift_voucher.voucher
    voucher.name = "User 1"
    voucher.message = "For you"
    voucher.save()
    assert gift_voucher.recipient_name == "User 1"
    assert gift_voucher.message == "For you"
    assert gift_voucher.start_date == datetime.today().strftime("%d-%b-%Y")
    assert not gift_voucher.expiry_date

    gift_voucher.activate()
    assert gift_voucher.start_date == datetime.today().strftime("%d-%b-%Y")
    assert gift_voucher.expiry_date == (datetime.today() + relativedelta(months=6)).strftime("%d-%b-%Y")



@pytest.mark.django_db 
def test_new_gift_voucher_creates_voucher(gift_voucher_types):
    gift_voucher = baker.make(GiftVoucher, gift_voucher_type=gift_voucher_types["total"])
    assert isinstance(gift_voucher.voucher, TotalVoucher)
    assert gift_voucher.voucher.discount_amount == 10

    gift_voucher = baker.make(GiftVoucher, gift_voucher_type=gift_voucher_types["regular_session"])
    assert isinstance(gift_voucher.voucher, ItemVoucher)
    assert gift_voucher.voucher.event_types == ["regular_session"]

    gift_voucher = baker.make(GiftVoucher, gift_voucher_type=gift_voucher_types["membership_2"])
    assert isinstance(gift_voucher.voucher, ItemVoucher)
    assert gift_voucher.voucher.membership_types.count() == 1


@pytest.mark.django_db 
def test_change_membership_on_gift_voucher(gift_voucher_types):
    gift_voucher = baker.make(GiftVoucher, gift_voucher_type=gift_voucher_types["membership_2"])
    assert gift_voucher.name == "Gift Voucher: test"
    voucher_id = gift_voucher.voucher.id
    gift_voucher.gift_voucher_type =gift_voucher_types["membership_4"]
    gift_voucher.save()
    assert gift_voucher.name == "Gift Voucher: test4"
    # new voucher created
    assert gift_voucher.voucher.id != voucher_id
    # old one was deleted
    assert ItemVoucher.objects.count() == 1
    assert gift_voucher.voucher.membership_types.count() == 1
    assert gift_voucher.voucher.membership_types.first().number_of_classes == 4
    

@pytest.mark.django_db 
def test_change_event_type_on_gift_voucher(gift_voucher_types):
    gift_voucher = baker.make(GiftVoucher, gift_voucher_type=gift_voucher_types["regular_session"])
    assert gift_voucher.name == "Gift Voucher: Class"
    voucher_id = gift_voucher.voucher.id
    gift_voucher.gift_voucher_type =gift_voucher_types["private"]
    gift_voucher.save()
    assert gift_voucher.name == "Gift Voucher: Private Lesson"
    # new voucher created
    assert gift_voucher.voucher.id != voucher_id
    # old one was deleted
    assert ItemVoucher.objects.count() == 1
    assert gift_voucher.voucher.event_types == ["private"]


@pytest.mark.django_db 
def test_change_voucher_type(gift_voucher_types):
    # membership voucher (ItemVoucher)
    gift_voucher = baker.make(GiftVoucher, gift_voucher_type=gift_voucher_types["membership_2"])
    assert isinstance(gift_voucher.voucher, ItemVoucher)

    # change to total voucher
    gift_voucher.gift_voucher_type = gift_voucher_types["total"]
    gift_voucher.save()
    assert ItemVoucher.objects.exists() is False
    assert isinstance(gift_voucher.voucher, TotalVoucher)

    # change to event type voucher (ItemVoucher)
    gift_voucher.gift_voucher_type = gift_voucher_types["private"]
    gift_voucher.save()
    assert TotalVoucher.objects.exists() is False
    assert isinstance(gift_voucher.voucher, ItemVoucher)
    assert gift_voucher.voucher.event_types == ["private"]

    # change event type (ItemVoucher)
    gift_voucher.gift_voucher_type = gift_voucher_types["regular_session"]
    gift_voucher.save()
    assert TotalVoucher.objects.exists() is False
    assert isinstance(gift_voucher.voucher, ItemVoucher)
    assert ItemVoucher.objects.count() == 1
    assert gift_voucher.voucher.event_types == ["regular_session"]

    # change to total voucher
    gift_voucher.gift_voucher_type = gift_voucher_types["total"]
    gift_voucher.save()
    assert ItemVoucher.objects.exists() is False
    assert isinstance(gift_voucher.voucher, TotalVoucher)

   # change to membership voucher (ItemVoucher)
    gift_voucher.gift_voucher_type = gift_voucher_types["membership_4"]
    gift_voucher.save()
    assert TotalVoucher.objects.exists() is False
    assert isinstance(gift_voucher.voucher, ItemVoucher)
    assert ItemVoucher.objects.count() == 1
    assert gift_voucher.voucher.membership_types.count() == 1
    assert gift_voucher.voucher.membership_types.first().number_of_classes == 4


@pytest.mark.django_db 
def test_create_gift_voucher_from_existing_total_voucher(gift_voucher_types):
    # voucher matches gift voucher type
    total_voucher = baker.make(TotalVoucher, discount_amount=10, is_gift_voucher=False)
    gift_voucher = baker.make(
        GiftVoucher, gift_voucher_type=gift_voucher_types["total"],
        total_voucher=total_voucher
    )
    assert gift_voucher.voucher.id == total_voucher.id
    total_voucher.refresh_from_db()
    assert total_voucher.is_gift_voucher
    
    # voucher mismatch
    total_voucher = baker.make(TotalVoucher, discount_amount=20, is_gift_voucher=False)
    gift_voucher = baker.make(
        GiftVoucher, gift_voucher_type=gift_voucher_types["total"],
        total_voucher=total_voucher
    )
    assert gift_voucher.voucher.id != total_voucher.id
    assert gift_voucher.voucher.discount_amount == 10


@pytest.mark.django_db 
def test_create_gift_voucher_from_existing_event_type_voucher(gift_voucher_types):
    # voucher matches gift voucher type
    voucher = baker.make(
        ItemVoucher, event_types=["private"], is_gift_voucher=False, discount=10
    )
    gift_voucher = baker.make(
        GiftVoucher, gift_voucher_type=gift_voucher_types["private"],
        item_voucher=voucher
    )
    assert gift_voucher.voucher.id == voucher.id
    voucher.refresh_from_db()
    assert voucher.is_gift_voucher
    assert ItemVoucher.objects.count() == 1

    # voucher mismatch
    voucher = baker.make(
        ItemVoucher, event_types=["private", "regular_session"], is_gift_voucher=False,
        discount=10
    )
    gift_voucher = baker.make(
        GiftVoucher, gift_voucher_type=gift_voucher_types["private"],
        item_voucher=voucher
    )
    assert gift_voucher.voucher.id != voucher.id
    assert ItemVoucher.objects.count() == 2


@pytest.mark.django_db 
def test_create_gift_voucher_from_existing_membership_voucher(gift_voucher_types, membership_type):
    # voucher matches gift voucher type
    voucher = baker.make(ItemVoucher, is_gift_voucher=False, discount=10)
    voucher.membership_types.add(membership_type)
    gift_voucher = baker.make(
        GiftVoucher, gift_voucher_type=gift_voucher_types["membership_2"],
        item_voucher=voucher
    )
    assert gift_voucher.voucher.id == voucher.id
    voucher.refresh_from_db()
    assert voucher.is_gift_voucher
    assert ItemVoucher.objects.count() == 1

    # voucher mismatch
    voucher = baker.make(ItemVoucher, is_gift_voucher=False, discount=10)
    voucher.membership_types.add(membership_type)
    gift_voucher = baker.make(
        GiftVoucher, gift_voucher_type=gift_voucher_types["membership_4"],
        item_voucher=voucher
    )
    assert gift_voucher.voucher.id != voucher.id
    assert ItemVoucher.objects.count() == 2


@pytest.mark.django_db 
def test_gift_voucher_activate(gift_voucher_types):
    gift_voucher = baker.make(GiftVoucher, gift_voucher_type=gift_voucher_types["membership_2"])
    start_date = timezone.now() - timedelta(weeks=6)
    gift_voucher.voucher.start_date = start_date
    gift_voucher.voucher.save()
    assert gift_voucher.voucher.expiry_date is None
    assert gift_voucher.paid is False
    assert gift_voucher.voucher.activated is False
    gift_voucher.activate()

    gift_voucher.refresh_from_db()
    assert gift_voucher.voucher.activated is True
    assert gift_voucher.voucher.expiry_date is not None
    assert gift_voucher.voucher.start_date > start_date


@pytest.mark.django_db 
def test_gift_voucher_name(gift_voucher_types):
    gift_voucher = baker.make(GiftVoucher, gift_voucher_type=gift_voucher_types["private"])
    assert gift_voucher.name == "Gift Voucher: Private Lesson"

    gift_voucher = baker.make(GiftVoucher, gift_voucher_type=gift_voucher_types["membership_2"])
    assert gift_voucher.name == "Gift Voucher: test"

    gift_voucher1 = baker.make(GiftVoucher, gift_voucher_type=gift_voucher_types["total"])
    assert gift_voucher1.name == "Gift Voucher: £10"


@pytest.mark.django_db 
def test_gift_voucher_str(gift_voucher_types):
    gift_voucher = baker.make(GiftVoucher, gift_voucher_type=gift_voucher_types["private"])
    gift_voucher.voucher.purchaser_email = "foo@bar.com"
    gift_voucher.save()
    assert str(gift_voucher) == f"{gift_voucher.voucher.code} - Gift Voucher: Private Lesson - foo@bar.com"

    gift_voucher1 = baker.make(GiftVoucher, gift_voucher_type=gift_voucher_types["total"])
    gift_voucher1.voucher.purchaser_email = "foo@bar.com"
    gift_voucher1.save()
    assert str(gift_voucher1) == f"{gift_voucher1.voucher.code} - Gift Voucher: £10 - foo@bar.com"


@pytest.mark.django_db 
def test_delete_gift_voucher(gift_voucher_types):
    gift_voucher = baker.make(GiftVoucher, gift_voucher_type=gift_voucher_types["private"])
    assert ItemVoucher.objects.count() == 1
    gift_voucher.delete()
    assert ItemVoucher.objects.count() == 0


@pytest.mark.django_db 
def test_delete_gift_voucher(gift_voucher_types):
    gvt = gift_voucher_type=gift_voucher_types["total"]
    gvt.override_cost = 40
    gvt.save()
    gift_voucher = baker.make(GiftVoucher, gift_voucher_type=gvt)
    assert gift_voucher.voucher.discount_amount == 10
    assert gift_voucher.gift_voucher_type.cost == 40
