# -*- coding: utf-8 -*-
from datetime import datetime, UTC

import pytest
from model_bakery import baker

from django.contrib.auth.models import User, AnonymousUser
from django.urls import reverse
from django.test import TestCase

from booking.models import Membership
from booking.templatetags.bookingtags import book_button_data


pytestmark = pytest.mark.django_db


class BookingtagTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        super(BookingtagTests, cls).setUpTestData()
        cls.user = baker.make(User, is_staff=True)
        cls.user.save()

    def _get_response(self, user, event):
        self.client.force_login(self.user)
        url = reverse("booking:event_detail", args=[event.slug])
        return self.client.get(url)

    def test_cancellation_format_tag_event_detail(self):
        """
        Test that cancellation period is formatted correctly
        """
        event = baker.make_recipe("booking.future_EV", cancellation_period=24)
        resp = self._get_response(self.user, event)
        resp.render()
        self.assertIn("24 hours", str(resp.content))

        event = baker.make_recipe("booking.future_EV", cancellation_period=25)
        resp = self._get_response(self.user, event)
        resp.render()
        self.assertIn("1 day and 1 hour", str(resp.content))

        event = baker.make_recipe("booking.future_EV", cancellation_period=48)
        resp = self._get_response(self.user, event)
        resp.render()
        self.assertIn("2 days", str(resp.content))

        event = baker.make_recipe("booking.future_EV", cancellation_period=619)
        resp = self._get_response(self.user, event)
        resp.render()
        self.assertIn("3 weeks, 4 days and 19 hours", str(resp.content))

        event = baker.make_recipe("booking.future_EV", cancellation_period=168)
        resp = self._get_response(self.user, event)
        resp.render()
        self.assertIn("1 week", str(resp.content))

        event = baker.make_recipe("booking.future_EV", cancellation_period=192)
        resp = self._get_response(self.user, event)
        resp.render()
        self.assertIn("1 week, 1 day and 0 hours", str(resp.content))


def button_data(event, **kwargs):
    data = {
        "show_book_button": True,
        "ref": "event",
        "event": event,
        "members_only_not_allowed": False,
        "is_booked": False,
        "can_cancel": False,
        "can_rebook": False,
        "can_book": False,
        "can_go_to_basket": False,
        "can_add_to_basket": False,
        "show_cancellation_warning": False,
        "on_waiting_list": False,
    }
    data.update(**kwargs)
    return data


def test_book_button_data_anon_user():
    user = AnonymousUser()
    event = baker.make_recipe("booking.future_PC")
    assert book_button_data(event, user, None, "event") == button_data(event)


def test_book_button_data_cancelled_event(configured_user):
    event = baker.make_recipe("booking.future_PC", cancelled=True)
    assert book_button_data(event, configured_user, None, "event") == button_data(
        event, show_book_button=False
    )


@pytest.mark.parametrize(
    "has_membership,members_only",
    [(True, False), (True, True), (False, False), (False, True)],
)
def test_book_button_data_never_booked(configured_user, has_membership, members_only):
    event = baker.make_recipe("booking.future_PC", members_only=members_only)
    if has_membership:
        baker.make(
            Membership,
            user=configured_user,
            paid=True,
            month=event.date.month,
            year=event.date.year,
        )
    assert book_button_data(event, configured_user, None, "event") == button_data(
        event,
        can_book=has_membership,
        can_add_to_basket=not has_membership,
        members_only_not_allowed=members_only and not has_membership,
    )


@pytest.mark.parametrize(
    "has_membership,members_only",
    [(True, False), (True, True), (False, False), (False, True)],
)
def test_book_button_data_booked(configured_user, has_membership, members_only):
    event = baker.make_recipe("booking.future_PC", members_only=members_only)
    booking = baker.make_recipe(
        "booking.booking", paid=True, event=event, user=configured_user
    )
    if has_membership:
        membership = baker.make(
            Membership,
            user=configured_user,
            paid=True,
            month=event.date.month,
            year=event.date.year,
        )
        booking.membership = membership
        booking.save()
    assert book_button_data(event, configured_user, booking, "event") == button_data(
        event,
        is_booked=True,
        can_cancel=True,
    )


@pytest.mark.freeze_time("2026-02-22T10:00")
@pytest.mark.parametrize(
    "event_date,cancellation_fee,show_warning",
    [
        # > 24 hrs away
        (datetime(2026, 2, 23, 12, 0, tzinfo=UTC), 1, False),
        # < 24 hrs away, no fee
        (datetime(2026, 2, 23, 12, 0, tzinfo=UTC), 0, False),
        # < 24 hrs away, has fee
        (datetime(2026, 2, 23, 12, 0, tzinfo=UTC), 1, False),
    ],
)
def test_book_button_data_cancellation_warning(
    configured_user, event_date, cancellation_fee, show_warning
):
    event = baker.make_recipe(
        "booking.future_PC", date=event_date, cancellation_fee=cancellation_fee
    )
    booking = baker.make_recipe(
        "booking.booking", paid=True, event=event, user=configured_user
    )
    assert book_button_data(event, configured_user, booking, "event") == button_data(
        event, is_booked=True, can_cancel=True, show_cancellation_warning=show_warning
    )


@pytest.mark.parametrize(
    "has_membership,status,no_show",
    [
        (True, "CANCELLED", False),
        (True, "OPEN", True),
        (False, "CANCELLED", False),
        (False, "OPEN", True),
    ],
)
def test_book_button_data_booking_cancelled(
    configured_user, has_membership, status, no_show
):
    event = baker.make_recipe("booking.future_PC")
    booking = baker.make_recipe(
        "booking.booking",
        status=status,
        paid=no_show,
        no_show=no_show,
        event=event,
        user=configured_user,
    )
    if has_membership:
        membership = baker.make(
            Membership,
            user=configured_user,
            paid=True,
            month=event.date.month,
            year=event.date.year,
        )
        if no_show:
            booking.membership = membership
            booking.save()
    assert book_button_data(event, configured_user, booking, "event") == button_data(
        event, can_rebook=has_membership, can_add_to_basket=not has_membership
    )
