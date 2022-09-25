# -*- coding: utf-8 -*-
from datetime import timedelta
from telnetlib import SE
from model_bakery import baker
from unittest.mock import Mock, patch

from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.urls import reverse
from django.test import TestCase, override_settings
from django.utils import timezone

from stripe.error import InvalidRequestError

from accounts.models import DataPrivacyPolicy
from booking.models import (
    Booking, Event, GiftVoucher, TotalVoucher, ItemVoucher, MembershipType, Membership
)
from .helpers import TestSetupMixin, make_disclaimer_content, make_data_privacy_agreement, make_online_disclaimer
from stripe_payments.models import Invoice, Seller


class ShoppingBasketMixin:

    def setUp(self):
        make_disclaimer_content()
        make_data_privacy_agreement(self.user)
        make_online_disclaimer(user=self.user)
        self.client.login(username=self.user.username, password="test")
        self.membership_type = baker.make(MembershipType, name="4 per month", number_of_classes=4, cost=20)
        future = timezone.now() + timedelta(1)
        past = timezone.now() - timedelta(1)
        self.regular_class = baker.make(Event, event_type="regular_session", cost=10, date=future)
        self.past_class = baker.make(Event, event_type="regular_session", cost=10, date=past)
        self.workshop = baker.make(Event, event_type="workshop", cost=20, date=future)
        self.private = baker.make(Event, event_type="private", cost=30, date=future)


class ShoppingBasketViewTests(ShoppingBasketMixin, TestSetupMixin, TestCase):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.url = reverse('booking:shopping_basket')

    def test_not_logged_in(self):
        self.client.logout()
        resp = self.client.get(self.url)
        assert resp.status_code == 302
        assert resp.url == f"{reverse('account_login')}?next={self.url}"
    
    def test_not_logged_in_gift_voucher(self):
        self.client.logout()
        gift_voucher = baker.make_recipe("booking.gift_voucher_10")
        session = self.client.session
        session.update({"purchases": {"gift_vouchers": [gift_voucher.id]}})
        session.save()
        resp = self.client.get(self.url)
        assert resp.status_code == 302
        assert resp.url == reverse("booking:guest_shopping_basket")

    def test_no_unpaid_items(self):
        resp = self.client.get(self.url)
        assert list(resp.context_data["unpaid_membership_info"]) == []
        assert list(resp.context_data["unpaid_booking_info"]) == []
        assert list(resp.context_data["applied_voucher_codes_and_discount"]) == []
        assert resp.context_data["total_cost"] == 0
        assert "Your cart is empty" in resp.rendered_content

    def test_with_unpaid_memberships(self):
        now = timezone.now()
        membership = baker.make(
            Membership, membership_type=self.membership_type, user=self.user,
            month=now.month, year=now.year, paid=False
        )
        resp = self.client.get(self.url)
        assert list(resp.context_data["unpaid_membership_info"]) == [
            {"membership": membership, "original_cost": 20, "voucher_applied": {"code": None, "discounted_cost": None}}
        ]

        assert list(resp.context_data["applied_voucher_codes_and_discount"]) == []
        assert resp.context_data["total_cost"] == 20

    def test_with_unpaid_bookings(self):
        booking = baker.make(Booking, event=self.regular_class, user=self.user, paid=False)
        # bookings for past events aren't included in the counts of unpaid bookings
        baker.make(Booking, event=self.past_class, user=self.user, paid=False)

        resp = self.client.get(self.url)
        assert list(resp.context_data["unpaid_membership_info"]) == []
        assert list(resp.context_data["unpaid_booking_info"]) == [
            {"booking": booking, "original_cost": 10, "voucher_applied": {"code": None, "discounted_cost": None}}
        ]
        assert list(resp.context_data["applied_voucher_codes_and_discount"]) == []
        assert resp.context_data["total_cost"] == 10
    
    def test_with_unpaid_items(self):
        now = timezone.now()
        membership = baker.make(
            Membership, membership_type=self.membership_type, user=self.user,
            month=now.month, year=now.year, paid=False
        )
        booking1 = baker.make(Booking, event=self.regular_class, user=self.user, paid=False)
        booking2 = baker.make(Booking, event=self.workshop, user=self.user, paid=False)
        booking3 = baker.make(Booking, event=self.private, user=self.user, paid=False)

        resp = self.client.get(self.url)
        assert list(resp.context_data["unpaid_membership_info"]) == [
            {"membership": membership, "original_cost": 20, "voucher_applied": {"code": None, "discounted_cost": None}}
        ]
        assert list(resp.context_data["unpaid_booking_info"]) == [
            {"booking": booking1, "original_cost": 10, "voucher_applied": {"code": None, "discounted_cost": None}},
            {"booking": booking2, "original_cost": 20, "voucher_applied": {"code": None, "discounted_cost": None}},
            {"booking": booking3, "original_cost": 30, "voucher_applied": {"code": None, "discounted_cost": None}}
        ]
        assert list(resp.context_data["applied_voucher_codes_and_discount"]) == []
        assert resp.context_data["total_cost"] == 80

    def test_cleans_up_expired_bookings(self):
        now = timezone.now()
        event_date = now + timedelta(1)
        # booked > 15 mins ago
        baker.make(
            "booking.booking", 
            event__date=event_date,
            paid=False, 
            date_booked=now - timedelta(minutes=30), user=self.user
        )
        # booked > 15 mins ago, rebooked < 15 mins ago
        rebooking = baker.make(
            "booking.booking", paid=False, 
            event__date=event_date,
            date_booked=now - timedelta(minutes=30),
            date_rebooked = now - timedelta(minutes=10),
            user=self.user
        )
        # booked > 15 mins ago, but checkout_time < 5 mins ago
        checkedout_booking = baker.make(
            "booking.booking", paid=False, 
            event__date=event_date,
            date_booked=now - timedelta(minutes=30),
            checkout_time=now - timedelta(minutes=2),
            user=self.user
        )
        assert self.user.bookings.count() == 3
        resp = self.client.get(self.url)
        self.user.refresh_from_db()
        assert self.user.bookings.count() == 2
        assert [
            unpaid["booking"] for unpaid in resp.context_data["unpaid_booking_info"]
        ] == [rebooking, checkedout_booking]

    def test_voucher_application(self):
        voucher = baker.make(ItemVoucher, code="test", discount=50)
        voucher.membership_types.add(self.membership_type)
        now = timezone.now()
        membership = baker.make(
            Membership, membership_type=self.membership_type, user=self.user,
            month=now.month, year=now.year, paid=False
        )

        resp = self.client.get(self.url)
        assert resp.context_data["total_cost"] == 20

        resp = self.client.post(self.url, data={"add_voucher_code": "add_voucher_code", "code": "test"})
        assert list(resp.context_data["unpaid_membership_info"]) == [
            {"membership": membership, "original_cost": 20, "voucher_applied": {"code": "test", "discounted_cost": 10}}
        ]
        assert list(resp.context_data["applied_voucher_codes_and_discount"]) == [("test", 50, None)]
        assert resp.context_data["total_cost"] == 10
        membership.refresh_from_db()
        assert membership.voucher == voucher

    def test_voucher_application_fixed_amount(self):
        voucher = baker.make(ItemVoucher, code="test", discount_amount=5)
        voucher.event_types = ["regular_session", "private"]
        voucher.save()
        booking1 = baker.make(Booking, event=self.regular_class, user=self.user, paid=False)
        booking2 = baker.make(Booking, event=self.workshop, user=self.user, paid=False)
        booking3 = baker.make(Booking, event=self.private, user=self.user, paid=False)

        resp = self.client.get(self.url)
        assert resp.context_data["total_cost"] == 60

        resp = self.client.post(self.url, data={"add_voucher_code": "add_voucher_code", "code": "test"})
        assert list(resp.context_data["unpaid_booking_info"]) == [
            {"booking": booking1, "original_cost": 10, "voucher_applied": {"code": "test", "discounted_cost": 5}},
            {"booking": booking2, "original_cost": 20, "voucher_applied": {"code": None, "discounted_cost": None}},
            {"booking": booking3, "original_cost": 30, "voucher_applied": {"code": "test", "discounted_cost": 25}}
        ]
        assert list(resp.context_data["applied_voucher_codes_and_discount"]) == [("test", None, 5)]
        assert resp.context_data["total_cost"] == 50
        for booking in [booking1, booking2, booking3]:
            booking.refresh_from_db()
        assert booking1.voucher == voucher
        assert booking2.voucher is None
        assert booking3.voucher == voucher

    def test_total_voucher_application(self):
        voucher = baker.make(TotalVoucher, code="test", discount=50)
        membership = baker.make_recipe(
            "booking.membership", membership_type=self.membership_type, user=self.user,
        )        
        resp = self.client.get(self.url)
        assert resp.context_data["total_cost"] == 20

        resp = self.client.post(self.url, data={"add_voucher_code": "add_voucher_code", "code": "test"})
        # no voucher code for block
        assert list(resp.context_data["unpaid_membership_info"]) == [
            {"membership": membership, "original_cost": 20, 'voucher_applied': {'code': None, 'discounted_cost': None}}
        ]
        # but voucher code here because it's a total one
        assert list(resp.context_data["applied_voucher_codes_and_discount"]) == [("test", 50, None)]
        assert resp.context_data['total_cost_without_total_voucher'] == 20
        assert resp.context_data["total_cost"] == 10

        membership.refresh_from_db()
        assert membership.voucher is None
        assert self.client.session["total_voucher_code"] == "test"

    def test_remove_voucher(self):
        voucher = baker.make(ItemVoucher, code="test", discount=50)
        voucher.membership_types.add(self.membership_type)
        membership = baker.make_recipe(
            "booking.membership", membership_type=self.membership_type, user=self.user,
            voucher=voucher
        )        

        resp = self.client.get(self.url)
        assert resp.context_data["total_cost"] == 10  # discount applied

        # adding it again doesn't do anything
        resp = self.client.post(self.url, data={"add_voucher_code": "add_voucher_code", "code": "test"})
        assert resp.context_data["total_cost"] == 10

        # remove it
        resp = self.client.post(self.url, data={"remove_voucher_code": "remove_voucher_code", "code": "test"})
        assert resp.context_data["total_cost"] == 20
        membership.refresh_from_db()
        assert membership.voucher is None

    def test_remove_total_voucher(self):
        baker.make(TotalVoucher, code="test", discount=50)
        membership = baker.make_recipe(
            "booking.membership", membership_type=self.membership_type, user=self.user,
        )          
        resp = self.client.post(self.url, data={"add_voucher_code": "add_voucher_code", "code": "test"})
        assert resp.context_data["total_cost"] == 10  # discount applied
        assert resp.context_data['total_cost_without_total_voucher'] == 20
        assert self.client.session["total_voucher_code"] == "test"

        # remove it
        resp = self.client.post(self.url, data={"remove_voucher_code": "remove_voucher_code", "code": "test"})
        assert resp.context_data["total_cost"] == 20
        assert "total_voucher_code" not in self.client.session

    def test_voucher_whitespace_removed(self):
        voucher = baker.make(ItemVoucher, code="test", discount=50)
        voucher.membership_types.add(self.membership_type)
        membership = baker.make_recipe(
            "booking.membership", membership_type=self.membership_type, user=self.user,
            voucher=voucher
        ) 
        resp = self.client.post(self.url, data={"add_voucher_code": "add_voucher_code", "code": "  test  "})
        assert list(resp.context_data["unpaid_membership_info"]) == [
            {"membership": membership, "original_cost": 20, "voucher_applied": {"code": "test", "discounted_cost": 10}}
        ]
        assert list(resp.context_data["applied_voucher_codes_and_discount"]) == [("test", 50, None)]
        assert resp.context_data["total_cost"] == 10

    def test_existing_voucher_removed_from_membership_if_invalid(self):
        voucher = baker.make(ItemVoucher, code="test", discount=50)
        voucher.membership_types.add(self.membership_type)
        membership = baker.make_recipe(
            "booking.membership", membership_type=self.membership_type, user=self.user,
            voucher=voucher
        ) 
        voucher.activated = False
        voucher.save()
        resp = self.client.get(self.url)
        assert resp.context_data["total_cost"] == 20  # discount not applied
        membership.refresh_from_db()
        assert membership.voucher is None

    def test_refresh_voucher(self):
        voucher = baker.make(ItemVoucher, code="test", discount=50)
        voucher.membership_types.add(self.membership_type)
        membership = baker.make_recipe(
            "booking.membership", membership_type=self.membership_type, user=self.user,
            voucher=voucher
        ) 
        resp = self.client.get(self.url)
        assert resp.context_data["total_cost"] == 10  # discount applied

        voucher.activated = False
        voucher.save()
        resp = self.client.post(self.url, {"code": "test", "refresh_voucher_code": True})
        assert resp.context_data["total_cost"] == 20  # discount not applied
        membership.refresh_from_db()
        assert membership.voucher is None

    def test_voucher_validation(self):
        voucher = baker.make(ItemVoucher, code="test", discount=50, activated=False)

        Membership.objects.all().delete()
        Booking.objects.all().delete()
        baker.make_recipe(
            "booking.membership", membership_type=self.membership_type,
            user=self.user,  # cost = 20
        )
        baker.make(Booking, event=self.regular_class, user=self.user) # cost = 10
        # unpaid booking with the voucher applied but for another user should have no impack
        baker.make(Booking, event=self.regular_class, paid=False, voucher=voucher)

        # invalid code
        resp = self.client.post(self.url, data={"add_voucher_code": "add_voucher_code", "code": "foo"})
        assert resp.context_data["voucher_add_error"] == ['"foo" is not a valid code']
        assert resp.context_data["total_cost"] == 30

        # not activated yet
        resp = self.client.post(self.url, data={"add_voucher_code": "add_voucher_code", "code": voucher.code})
        assert resp.context_data["voucher_add_error"] == ["Voucher has not been activated yet"]
        assert resp.context_data["total_cost"] == 30

        # voucher not valid for any blocks
        voucher.activated = True
        voucher.save()
        resp = self.client.post(self.url, data={"add_voucher_code": "add_voucher_code", "code": voucher.code})
        assert resp.context_data["voucher_add_error"] == [f"Code '{voucher.code}' is not valid for any items in your cart"]
        assert resp.context_data["total_cost"] == 30

        # voucher not started
        voucher.membership_types.add(self.membership_type)
        voucher.start_date = timezone.now() + timedelta(2)
        voucher.save()
        resp = self.client.post(self.url, data={"add_voucher_code": "add_voucher_code", "code": voucher.code})
        assert resp.context_data["voucher_add_error"] == [
            f"Voucher code is not valid until {voucher.start_date.strftime('%d %b %y')}"
        ]
        assert resp.context_data["total_cost"] == 30

        # voucher expired
        voucher.start_date = timezone.now() - timedelta(5)
        voucher.expiry_date = timezone.now() - timedelta(2)
        voucher.save()
        resp = self.client.post(self.url, data={"add_voucher_code": "add_voucher_code", "code": voucher.code})
        assert resp.context_data["voucher_add_error"] == [f"Voucher has expired"]
        assert resp.context_data["total_cost"] == 30

        # voucher max uses per user expired
        voucher.expiry_date = None
        voucher.max_per_user = 1
        voucher.event_types = ["regular_session", "workshop", "private"]
        voucher.save()

        resp = self.client.post(self.url, data={"add_voucher_code": "add_voucher_code", "code": voucher.code})
        assert resp.context_data["voucher_add_error"] == [
            f"Voucher code {voucher.code} already used max number of times (limited to 1 per user)"
        ]

        # voucher existing unpaid item voucher already applied
        voucher.expiry_date = None
        voucher.max_per_user = 3
        voucher.save()

        # voucher applied to one booking already paid.  With the 1 unpaid booking and 1 unpaid membership already
        # created in this test, this will make the total max per user 3, allowed
        baker.make(
            Booking, event=self.workshop, user=self.user,
            voucher=voucher, paid=True
        )
        resp = self.client.post(
            self.url, data={"add_voucher_code": "add_voucher_code", "code": voucher.code}
        )
        assert resp.context_data["voucher_add_error"] == []
        # voucher applied to the two unpaid items
        assert resp.context_data["total_cost"] == 15

        # voucher max total uses expired
        voucher.max_per_user = None
        voucher.max_vouchers = 3
        voucher.save()
        baker.make(
            Booking, event=self.private, user=self.user,
            voucher=voucher, paid=False
        )

        # voucher used for only some items before it's used up
        assert voucher.uses() == 1 # (1 paid item already, 3 unpaid items in cart)

        resp = self.client.post(self.url, data={"add_voucher_code": "add_voucher_code", "code": voucher.code})
        assert resp.context_data["voucher_add_error"] == [
            f"Voucher code {voucher.code} has limited number of total uses and expired before it could be used for all applicable items"
        ]
        # 50% discount applied to 2 of the 3 items only (it'll be removed from the first), 
        # total == 20 (full price membership) + 5 (discounted class) + 15 (full price private)
        assert resp.context_data["total_cost"] == 40

    def test_total_voucher_validation(self):
        voucher = baker.make(TotalVoucher, code="test_amount", discount_amount=10, activated=False)
        baker.make_recipe(
            "booking.membership", membership_type=self.membership_type,
            user=self.user,  # cost = 20
        )
        baker.make(Booking, event=self.regular_class, user=self.user) # cost = 10

        # invalid code
        resp = self.client.post(self.url, data={"add_voucher_code": "add_voucher_code", "code": "foo"})
        assert resp.context_data["voucher_add_error"] == ['"foo" is not a valid code']
        assert resp.context_data["total_cost"] == 30

        # not activated yet
        resp = self.client.post(self.url, data={"add_voucher_code": "add_voucher_code", "code": voucher.code})
        assert resp.context_data["voucher_add_error"] == ["Voucher has not been activated yet"]
        assert resp.context_data["total_cost"] == 30

        voucher.activated = True
        voucher.save()

        # voucher not started
        voucher.start_date = timezone.now() + timedelta(2)
        voucher.save()
        resp = self.client.post(self.url, data={"add_voucher_code": "add_voucher_code", "code": voucher.code})
        assert resp.context_data["voucher_add_error"] == [
            f"Voucher code is not valid until {voucher.start_date.strftime('%d %b %y')}"
        ]
        assert resp.context_data["total_cost"] == 30

        # voucher expired
        voucher.start_date = timezone.now() - timedelta(5)
        voucher.expiry_date = timezone.now() - timedelta(2)
        voucher.save()
        resp = self.client.post(self.url, data={"add_voucher_code": "add_voucher_code", "code": voucher.code})
        assert resp.context_data["voucher_add_error"] == [f"Voucher has expired"]
        assert resp.context_data["total_cost"] == 30

        # voucher max uses per user expired
        voucher.expiry_date = None
        voucher.max_per_user = 1
        voucher.save()
        baker.make(
            Invoice, username=self.user.email, total_voucher_code=voucher.code, paid=True
        )
        resp = self.client.post(self.url, data={"add_voucher_code": "add_voucher_code", "code": voucher.code})
        assert resp.context_data["voucher_add_error"] == [
            f"You have already used voucher code {voucher.code} the maximum number of times (1)"]
        assert resp.context_data["total_cost"] == 30

        # voucher max total uses expired
        voucher.max_per_user = None
        voucher.max_vouchers = 2
        voucher.save()
        baker.make(
            Invoice, username=self.user.email, total_voucher_code=voucher.code, paid=True, _quantity=2
        )
        resp = self.client.post(self.url, data={"add_voucher_code": "add_voucher_code", "code": voucher.code})
        assert resp.context_data["voucher_add_error"] == [
            f"Voucher code {voucher.code} has limited number of total uses and has expired"]
        assert resp.context_data["total_cost"] == 30

    def test_total_voucher_greater_than_checkout_amount(self):
        voucher = baker.make(TotalVoucher, code="test_amount", discount_amount=5, activated=True)
        baker.make(Booking, event=self.regular_class, user=self.user)

        # class cost is 10, total shows block cost minus voucher
        resp = self.client.post(self.url, data={"add_voucher_code": "add_voucher_code", "code": "test_amount"})
        assert resp.context_data["total_cost"] == 5

        # voucher is valid for x2 block costs, total shows 0
        voucher.discount_amount = 20
        voucher.save()
        resp = self.client.post(self.url, data={"add_voucher_code": "add_voucher_code", "code": "test_amount"})
        assert resp.context_data["total_cost"] == 0

    def test_apply_voucher_to_multiple_bookings(self):
        future = timezone.now() + timedelta(1)
        # 10 each, voucher valid: 15 total
        baker.make(
            Booking, event__event_type="regular_session", 
            event__date=future, event__cost=10, user=self.user, _quantity=3
        )
        # 30 each, voucher not valid: 60 total
        baker.make(
            Booking, event__event_type="private", 
            event__date=future, event__cost=30, user=self.user, _quantity=2
        )
        # 20 each, voucher not valid, 20 total
        baker.make(Booking, event=self.workshop, user=self.user, _quantity=1)
        voucher = baker.make(
            ItemVoucher, code="test", discount=50, max_per_user=10, event_types=["regular_session"]
        )

        # code applied to regular sessions only
        resp = self.client.post(self.url, data={"add_voucher_code": "add_voucher_code", "code": "test"})
        assert resp.context_data["total_cost"] == 95

        # apply to workshop too
        voucher.event_types = ["regular_session", "workshop"]
        voucher.save()
        resp = self.client.post(self.url, data={"refresh_voucher_code": "refresh_voucher_code", "code": "test"})
        assert resp.context_data["total_cost"] == 85

    def test_apply_multiple_vouchers(self):
        voucher = baker.make(ItemVoucher, code="test", discount=50, max_per_user=10)
        voucher.membership_types.add(self.membership_type)
        # cost = 20 each, 60 total
        baker.make_recipe(
            "booking.membership", membership_type=self.membership_type, user=self.user,
            _quantity=3
        )
        # voucher applied
        resp = self.client.post(self.url, data={"add_voucher_code": "add_voucher_code", "code": "test"})
        assert resp.context_data["total_cost"] == 30

        # second valid voucher replaces the first
        voucher1 = baker.make(ItemVoucher, code="foo", discount=20, max_per_user=10)
        voucher1.membership_types.add(self.membership_type)
        resp = self.client.post(self.url, data={"add_voucher_code": "add_voucher_code", "code": "foo"})
        assert resp.context_data["total_cost"] == 48

    def test_apply_multiple_vouchers_to_different_items(self):
        voucher = baker.make(ItemVoucher, code="test", discount=50, max_per_user=10)
        voucher.membership_types.add(self.membership_type)
        baker.make(
            ItemVoucher, code="foo", discount=10, max_per_user=10, event_types=["regular_session"]
        )
        memberships = baker.make_recipe(
            "booking.membership", membership_type=self.membership_type, user=self.user,
            _quantity=2
        )
        regular_booking = baker.make(Booking, event=self.regular_class, user=self.user)
        private_booking = baker.make(Booking, event=self.private, user=self.user)

        resp = self.client.post(self.url, data={"add_voucher_code": "add_voucher_code", "code": "test"})
        # applied to memberships only
        assert list(resp.context_data["unpaid_membership_info"]) == [
            {"membership": memberships[0], "original_cost": 20, "voucher_applied": {"code": "test", "discounted_cost": 10}},
            {"membership": memberships[1], "original_cost": 20, "voucher_applied": {"code": "test", "discounted_cost": 10}}

        ]
        assert list(resp.context_data["unpaid_booking_info"]) == [
            {"booking": regular_booking, "original_cost": 10, "voucher_applied": {"code": None, "discounted_cost": None}},
            {"booking": private_booking, "original_cost": 30, "voucher_applied": {"code": None, "discounted_cost": None}}

        ]
        assert list(resp.context_data["applied_voucher_codes_and_discount"]) == [("test", 50, None)]
        assert resp.context_data["total_cost"] == 60

        # apply second voucher, applied to regular session booking only
        resp = self.client.post(self.url, data={"add_voucher_code": "add_voucher_code", "code": "foo"})
        # first code is still there
        assert list(resp.context_data["unpaid_membership_info"]) == [
            {"membership": memberships[0], "original_cost": 20, "voucher_applied": {"code": "test", "discounted_cost": 10}},
            {"membership": memberships[1], "original_cost": 20, "voucher_applied": {"code": "test", "discounted_cost": 10}}

        ]
        assert list(resp.context_data["unpaid_booking_info"]) == [
            {"booking": regular_booking, "original_cost": 10, "voucher_applied": {"code": "foo", "discounted_cost": 9}},
            {"booking": private_booking, "original_cost": 30, "voucher_applied": {"code": None, "discounted_cost": None}}

        ]
        assert sorted(resp.context_data["applied_voucher_codes_and_discount"]) == [("foo", 10, None), ("test", 50, None)]
        assert resp.context_data["total_cost"] == 59

    def test_stripe_payment_button_when_total_is_zero(self):
        voucher = baker.make(ItemVoucher, code="test", discount=50, max_per_user=10)
        voucher.membership_types.add(self.membership_type)
        membership = baker.make_recipe(
            "booking.membership", membership_type=self.membership_type, user=self.user,
        )

        resp = self.client.post(self.url, data={"add_voucher_code": "add_voucher_code", "code": "test"})
        assert resp.context_data["total_cost"] == 10
        assert "Checkout" in resp.rendered_content

        voucher.discount = 100
        voucher.save()
        resp = self.client.post(self.url, data={"add_voucher_code": "add_voucher_code", "code": "test"})
        assert resp.context_data["total_cost"] == 0
        assert "Checkout" not in resp.rendered_content
        assert "Submit" in resp.rendered_content


class GuestShoppingBasketTests(TestSetupMixin, TestCase):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.url = reverse("booking:guest_shopping_basket")

    def test_with_logged_in_user_no_purchases(self):
        self.client.login(username=self.user.username, password="test")
        resp = self.client.get(self.url)
        assert resp.status_code == 302
        assert resp.url == reverse("booking:shopping_basket")

        self.client.logout()
        resp = self.client.get(self.url)
        assert resp.status_code == 200

    def test_no_voucher(self):
        resp = self.client.get(self.url)
        assert resp.context_data["unpaid_items"] is False
        assert resp.context_data["unpaid_gift_voucher_info"] == []
        assert resp.context_data["total_cost"] == 0

    def test_with_voucher(self):
        session = self.client.session
        gift_voucher = baker.make_recipe("booking.gift_voucher_10")
        session.update({"purchases": {"gift_vouchers": [gift_voucher.id]}})
        session.save()
        resp = self.client.get(self.url)
        assert resp.context_data["unpaid_items"]
        assert resp.context_data["unpaid_gift_voucher_info"] == [
            {"gift_voucher": gift_voucher, "cost": 10}
        ]
        assert resp.context_data["total_cost"] == 10

    def test_with_multiple_vouchers(self):
        session = self.client.session
        gift_voucher1 = baker.make_recipe("booking.gift_voucher_10")
        gift_voucher2 = baker.make_recipe("booking.gift_voucher_11")
        session.update({"purchases": {"gift_vouchers": [gift_voucher1.id, gift_voucher2.id]}})
        session.save()
        resp = self.client.get(self.url)
        assert resp.context_data["unpaid_items"]
        assert resp.context_data["total_cost"] == 21
        assert resp.context_data["unpaid_gift_voucher_info"] == [
            {"gift_voucher": gift_voucher1, "cost": 10},
            {"gift_voucher": gift_voucher2, "cost": 11}
        ]

    def test_with_invalid_vouchers(self):
        session = self.client.session
        gift_voucher1 = baker.make_recipe("booking.gift_voucher_10", paid=True)
        gift_voucher2 = baker.make_recipe("booking.gift_voucher_11")
        session.update({"purchases": {"gift_vouchers": [gift_voucher1.id, gift_voucher2.id, 999]}})
        session.save()
        resp = self.client.get(self.url)
        assert resp.context_data["unpaid_items"]
        assert resp.context_data["total_cost"] == 11
        assert resp.context_data["unpaid_gift_voucher_info"] == [
            {"gift_voucher": gift_voucher2, "cost": 11}
        ]


class StripeCheckoutTests(ShoppingBasketMixin, TestSetupMixin, TestCase):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.url = reverse('booking:stripe_checkout')

    def get_mock_payment_intent(self, **params):
        defaults = {
            "id": "mock-intent-id",
            "amount": 1000,
            "description": "",
            "status": "succeeded",
            "metadata": {},
            "currency": "gbp",
            "client_secret": "secret"
        }
        options = {**defaults, **params}
        return Mock(**options)

    def setUp(self):
        super().setUp()
        baker.make(Seller, site=Site.objects.get_current())

    def test_anon_user_no_unpaid_items(self):
        self.client.logout()
        # If no unpaid items, ignore any cart total passed and return to shopping basket
        resp = self.client.post(self.url, data={"cart_total": 10})
        assert resp.status_code == 302
        assert resp.url == reverse("booking:guest_shopping_basket")

    def test_rechecks_total_anon_user(self):
        self.client.logout()
        session = self.client.session
        gift_voucher1 = baker.make_recipe("booking.gift_voucher_10")
        gift_voucher2 = baker.make_recipe("booking.gift_voucher_11")
        session.update(
            {"purchases": {"gift_vouchers": [gift_voucher1.id, gift_voucher2.id]}})
        session.save()

        # total is incorrect, redirect to basket again
        resp = self.client.post(self.url, data={"cart_total": 10})
        assert resp.status_code == 302
        # redirects to basket, which will do the redirect to guest basket
        assert resp.url == reverse("booking:shopping_basket")

    def test_logged_in_user_no_unpaid_items(self):
        # If no unpaid items, ignore any cart total passed and return to shopping basket
        resp = self.client.post(self.url, data={"cart_total": 10})
        assert resp.status_code == 302
        assert resp.url == reverse("booking:shopping_basket")

    @patch("booking.views.shopping_basket.stripe.PaymentIntent")
    def test_creates_invoice_and_applies_to_unpaid_items(self, mock_payment_intent):
        mock_payment_intent_obj = self.get_mock_payment_intent(id="foo")
        mock_payment_intent.create.return_value = mock_payment_intent_obj
        membership = baker.make_recipe(
            "booking.membership", membership_type=self.membership_type, user=self.user,
        )
        booking = baker.make(Booking, event=self.regular_class, user=self.user)

        assert Invoice.objects.exists() is False
        # total is correct
        resp = self.client.post(self.url, data={"cart_total": 30})
        assert resp.status_code == 200
        assert resp.context_data["cart_total"] == 30.00
        membership.refresh_from_db()
        booking.refresh_from_db()

        assert Invoice.objects.exists()
        invoice = Invoice.objects.first()
        assert invoice.username == self.user.email
        assert invoice.amount == 30
        assert membership.invoice == invoice
        assert booking.invoice == invoice

    @patch("booking.views.shopping_basket.stripe.PaymentIntent")
    def test_creates_invoice_and_applies_to_unpaid_gift_vouchers_anon_user(
            self, mock_payment_intent
    ):
        mock_payment_intent_obj = self.get_mock_payment_intent(id="foo")
        mock_payment_intent.create.return_value = mock_payment_intent_obj
        self.client.logout()
        session = self.client.session
        gift_voucher1 = baker.make_recipe("booking.gift_voucher_10")
        gift_voucher2 = baker.make_recipe("booking.gift_voucher_11")
        session.update(
            {"purchases": {"gift_vouchers": [gift_voucher1.id, gift_voucher2.id]}})
        session.save()

        assert Invoice.objects.exists() is False
        # total is correct
        resp = self.client.post(self.url, data={"cart_total": 21})
        assert resp.status_code == 200
        assert resp.context_data["cart_total"] == 21.00

        gift_voucher1.refresh_from_db()
        gift_voucher2.refresh_from_db()

        assert Invoice.objects.exists()
        invoice = Invoice.objects.first()
        assert invoice.username == ""
        assert invoice.amount == 21
        assert gift_voucher1.invoice == invoice
        assert gift_voucher2.invoice == invoice

    @patch("booking.views.shopping_basket.stripe.PaymentIntent")
    def test_creates_invoice_and_applies_to_unpaid_blocks_with_vouchers(self, mock_payment_intent):
        mock_payment_intent_obj = self.get_mock_payment_intent(id="foo")
        mock_payment_intent.create.return_value = mock_payment_intent_obj
        voucher = baker.make(ItemVoucher, discount=10, event_types=["private"])
        voucher.membership_types.add(self.membership_type)
        membership = baker.make_recipe(
            "booking.membership", membership_type=self.membership_type, user=self.user,
            voucher=voucher
        ) # 20, 18 with voucher
        booking_p = baker.make(
            Booking, event=self.private, user=self.user, voucher=voucher
        )  # 30, 27 with voucher 
        booking_w = baker.make(Booking, event=self.workshop, user=self.user) # 20

        assert Invoice.objects.exists() is False
        # total is correct
        resp = self.client.post(self.url, data={"cart_total": 65})
        assert resp.status_code == 200
        for item in [membership, booking_p, booking_w]:
            item.refresh_from_db()
        assert Invoice.objects.exists()
        invoice = Invoice.objects.first()
        assert invoice.username == self.user.email
        assert invoice.amount == 65
        for item in [membership, booking_p]:
            assert item.invoice == invoice
        assert resp.context_data["cart_total"] == 65.00

    @patch("booking.views.shopping_basket.stripe.PaymentIntent")
    def test_zero_total(self, mock_payment_intent):
        mock_payment_intent_obj = self.get_mock_payment_intent(id="foo")
        mock_payment_intent.create.return_value = mock_payment_intent_obj
        voucher = baker.make(ItemVoucher, code="test", discount=100, max_per_user=10, event_types=["private"])
        booking = baker.make(Booking, event=self.private, user=self.user, voucher=voucher)
        resp = self.client.post(self.url, data={"cart_total": 0})
        booking.refresh_from_db()
        assert booking.paid
        assert booking.voucher == voucher
        assert resp.status_code == 302
        assert resp.url == reverse("booking:regular_session_list")

    @patch("booking.views.shopping_basket.stripe.PaymentIntent")
    def test_zero_total_with_total_voucher(self, mock_payment_intent):
        mock_payment_intent_obj = self.get_mock_payment_intent(id="foo")
        mock_payment_intent.create.return_value = mock_payment_intent_obj
        baker.make(TotalVoucher, activated=True, code="test", discount_amount=100, max_per_user=10)
        booking = baker.make(Booking, event=self.private, user=self.user)
        membership = baker.make_recipe(
            "booking.membership", membership_type=self.membership_type, user=self.user,
        )
        gift_voucher = baker.make_recipe("booking.gift_voucher_10")
        gift_voucher.voucher.purchaser_email = self.user.email
        gift_voucher.voucher.save()
        
        # Call shopping basket view to apply the total voucher code
        self.client.post(reverse('booking:shopping_basket'), data={"add_voucher_code": "add_voucher_code", "code": "test"})
        assert self.client.session["total_voucher_code"] == "test"

        resp = self.client.post(self.url, data={"cart_total": 0})
        for item in [booking, membership]:
            item.refresh_from_db()
            assert item.paid is True
        assert gift_voucher.voucher.activated is True
        assert resp.status_code == 302
        assert resp.url == reverse("booking:regular_session_list")

        invoice = Invoice.objects.latest("id")
        assert membership in invoice.memberships.all()
        assert gift_voucher in invoice.gift_vouchers.all()
        assert booking in invoice.bookings.all()
        assert invoice.paid is True

    @patch("booking.views.shopping_basket.stripe.PaymentIntent")
    def test_uses_existing_invoice(self, mock_payment_intent):
        mock_payment_intent_obj = self.get_mock_payment_intent(id="foo")
        mock_payment_intent.modify.return_value = mock_payment_intent_obj
        invoice = baker.make(
            Invoice, username=self.user.email, amount=20, paid=False,
            stripe_payment_intent_id="foo"
        )
        booking = baker.make(Booking, event=self.private, user=self.user, invoice=invoice)

        # total is correct
        resp = self.client.post(self.url, data={"cart_total": 30})
        booking.refresh_from_db()
        assert Invoice.objects.count() == 1
        assert booking.invoice == invoice
        assert resp.context_data["cart_total"] ==30.00

    def test_no_seller(self):
        Seller.objects.all().delete()
        baker.make(Booking, event=self.private, user=self.user)

        resp = self.client.post(self.url, data={"cart_total": 30})
        assert resp.status_code == 200
        assert resp.context_data["preprocessing_error"] is True

    @patch("booking.views.shopping_basket.stripe.PaymentIntent")
    def test_invoice_already_succeeded(self, mock_payment_intent):
        mock_payment_intent_obj = self.get_mock_payment_intent(id="foo", status="succeeded")
        mock_payment_intent.modify.side_effect = InvalidRequestError("error", None)
        mock_payment_intent.retrieve.return_value = mock_payment_intent_obj

        invoice = baker.make(
            Invoice, username=self.user.email, amount=30, paid=False,
            stripe_payment_intent_id="foo"
        )
        baker.make(Booking, event=self.private, user=self.user, invoice=invoice)
        resp = self.client.post(self.url, data={"cart_total": 30})
        assert resp.context_data["preprocessing_error"] is True

    @patch("booking.views.shopping_basket.stripe.PaymentIntent")
    def test_other_error_modifying_payment_intent(self, mock_payment_intent):
        mock_payment_intent_obj = self.get_mock_payment_intent(id="foo", status="pending")
        mock_payment_intent.modify.side_effect = InvalidRequestError("error", None)
        mock_payment_intent.retrieve.return_value = mock_payment_intent_obj

        invoice = baker.make(
            Invoice, username=self.user.email, amount=30, paid=False,
            stripe_payment_intent_id="foo"
        )
        baker.make(Booking, event=self.private, user=self.user, invoice=invoice)
        
        resp = self.client.post(self.url, data={"cart_total": 30})
        assert resp.context_data["preprocessing_error"] is True

    def test_check_total(self):
        # This is the last check immediately before submitting payment; just returns the current total
        # so the js can check it
        url = reverse("booking:check_total")
        resp = self.client.get(url)
        assert resp.json() == {"total": 0}

        booking = baker.make(Booking, event=self.private, user=self.user)
        membership = baker.make_recipe(
            "booking.membership", membership_type=self.membership_type, user=self.user,
        )
        resp = self.client.get(url)
        assert resp.json() == {"total": "50.00"}

        booking.paid = True
        booking.save()
        voucher = baker.make(ItemVoucher, code="test", discount=10, max_per_user=10)
        voucher.membership_types.add(self.membership_type)
        membership.voucher = voucher
        membership.save()
        resp = self.client.get(url)
        assert resp.json() == {"total": "18.00"}

    def test_check_total_anon_user(self):
        self.client.logout()
        url = reverse("booking:check_total")
        resp = self.client.get(url)
        assert resp.json() == {"total": 0}

        session = self.client.session
        gift_voucher1 = baker.make_recipe("booking.gift_voucher_10")
        gift_voucher2 = baker.make_recipe("booking.gift_voucher_11")
        session.update(
            {"purchases": {"gift_vouchers": [gift_voucher1.id, gift_voucher2.id]}})
        session.save()

        url = reverse("booking:check_total")
        resp = self.client.get(url)
        assert resp.json() == {"total": "21.00"}
