from datetime import datetime, timedelta
from datetime import timezone as dt_timezone

from django.urls import reverse
from django.utils import timezone
from booking.models import Membership, RegularClass

import pytest
from model_bakery import baker


pytestmark = pytest.mark.django_db


# MembershipListView (views/membership_views.py)
def test_user_memberships_get(client, configured_user, membership_type):
    list_url = reverse("booking:user_memberships")
    client.force_login(configured_user)
    # unpaid
    baker.make_recipe("booking.membership", user=configured_user)
    paid = baker.make_recipe("booking.membership", user=configured_user, paid=True)
    last_month = timezone.now() - timedelta(days=32)
    expired = baker.make_recipe(
        "booking.membership",
        user=configured_user,
        paid=True,
        month=last_month.month,
        year=last_month.year,
    )
    full = baker.make_recipe(
        "booking.membership",
        membership_type=membership_type,
        user=configured_user,
        paid=True,
    )
    baker.make("Booking", membership=full, _quantity=2)

    # only shows paid, not-expired, not-full by default
    resp = client.get(list_url)
    assert [mem.id for mem in resp.context_data["memberships"]] == [paid.id]

    # show all except unpaid
    resp = client.get(list_url + "?include-expired=yes")
    assert sorted([mem.id for mem in resp.context_data["memberships"]]) == [
        paid.id,
        expired.id,
        full.id,
    ]


# MembershipDetailView (views/membership_views.py)
def test_detail_url(client, configured_user):
    membership = baker.make_recipe(
        "booking.membership", user=configured_user, paid=True
    )
    url = reverse("booking:membership_detail", args=(membership.id,))

    # login required
    resp = client.get(url)
    assert resp.status_code == 302

    client.force_login(configured_user)
    resp = client.get(url)
    assert resp.status_code == 200


# membership_purchase_view (views/purchases.py)
buy_url = reverse("booking:membership_purchase")


def test_membership_purchase_login_not_required(
    client, configured_user, membership_type
):
    resp = client.get(buy_url)
    assert resp.status_code == 200


def test_get_available_memberships_to_purchase(
    client, configured_user, membership_type, membership_type_4
):
    client.force_login(configured_user)
    resp = client.get(buy_url)

    # all membership types available
    assert len(resp.context["membership_types"]) == 2
    # only shows active
    membership_type.active = False
    membership_type.save()
    resp = client.get(buy_url)
    assert len(resp.context["membership_types"]) == 1


@pytest.mark.freeze_time("2020-10-01")
def test_membership_purchase_options(freezer, client, configured_user, membership_type):
    client.force_login(configured_user)
    # time is beginning of month, only shows one set of options
    resp = client.get(buy_url)
    options = resp.context_data["options"]
    assert len(options) == 1

    # time is end of month, there are no classes scheduled for the current
    # month, only shows next month as an option
    freezer.move_to("2020-10-27")
    client.force_login(configured_user)
    # time is beginning of month, shows next months options as well
    resp = client.get(buy_url)
    options = resp.context_data["options"]
    assert len(options) == 1

    assert options == [
        {
            "membership_type": membership_type,
            "month": 11,
            "month_str": "November",
            "warn_for_current": False,
            "year": 2020,
            "basket_count": 0,
        }
    ]

    # make a past class and a future class for next month; still only shows next month
    baker.make(RegularClass, date=datetime(2020, 10, 25, 10, 0, tzinfo=dt_timezone.utc))
    baker.make(RegularClass, date=datetime(2020, 11, 1, 10, 0, tzinfo=dt_timezone.utc))
    resp = client.get(buy_url)
    assert resp.context_data["options"] == [
        {
            "membership_type": membership_type,
            "month": 11,
            "month_str": "November",
            "warn_for_current": False,
            "year": 2020,
            "basket_count": 0,
        }
    ]

    # make a future class for this month
    future_class = baker.make(
        RegularClass, date=datetime(2020, 10, 30, 10, 0, tzinfo=dt_timezone.utc)
    )
    resp = client.get(buy_url)

    assert resp.context_data["options"] == [
        {
            "membership_type": membership_type,
            "month": 10,
            "month_str": "October",
            "warn_for_current": True,
            "year": 2020,
            "basket_count": 0,
        },
        {
            "membership_type": membership_type,
            "month": 11,
            "month_str": "November",
            "warn_for_current": False,
            "year": 2020,
            "basket_count": 0,
        },
    ]

    # end of year correctly assigns next month
    freezer.move_to("2020-12-27")
    # make sure we have a future class
    future_class.date = datetime(2020, 12, 30, 10, 0, tzinfo=dt_timezone.utc)
    future_class.save()
    client.force_login(configured_user)
    # time is beginning of month, shows next months options as well
    resp = client.get(buy_url)
    options = resp.context_data["options"]
    assert options == [
        {
            "membership_type": membership_type,
            "month": 12,
            "month_str": "December",
            "warn_for_current": True,
            "year": 2020,
            "basket_count": 0,
        },
        {
            "membership_type": membership_type,
            "month": 1,
            "month_str": "January",
            "warn_for_current": False,
            "year": 2021,
            "basket_count": 0,
        },
    ]


@pytest.mark.freeze_time("2020-10-29")
def test_membership_purchase_options_with_unpaid_items(
    client, configured_user, membership_type
):
    client.force_login(configured_user)
    # time is end of month, shows this month and next
    # make a future class for this month
    baker.make(RegularClass, date=datetime(2020, 10, 30, 10, 0, tzinfo=dt_timezone.utc))
    resp = client.get(buy_url)
    assert resp.context_data["options"] == [
        {
            "membership_type": membership_type,
            "month": 10,
            "month_str": "October",
            "warn_for_current": True,
            "year": 2020,
            "basket_count": 0,
        },
        {
            "membership_type": membership_type,
            "month": 11,
            "month_str": "November",
            "warn_for_current": False,
            "year": 2020,
            "basket_count": 0,
        },
    ]

    # make paid and unpaid memberships; only unpaid count in options display
    baker.make(
        Membership,
        membership_type=membership_type,
        user=configured_user,
        paid=False,
        month=10,
        year=2020,
    )
    baker.make(
        Membership,
        membership_type=membership_type,
        user=configured_user,
        paid=True,
        month=10,
        year=2020,
    )
    baker.make(
        Membership,
        membership_type=membership_type,
        user=configured_user,
        paid=False,
        month=11,
        year=2020,
    )
    resp = client.get(buy_url)
    assert resp.context_data["options"] == [
        {
            "membership_type": membership_type,
            "month": 10,
            "month_str": "October",
            "warn_for_current": True,
            "year": 2020,
            "basket_count": 1,
        },
        {
            "membership_type": membership_type,
            "month": 11,
            "month_str": "November",
            "warn_for_current": False,
            "year": 2020,
            "basket_count": 1,
        },
    ]


# ajax_add_membership_to_basket (views/purchases.py)
add_url = reverse("booking:ajax_add_membership_to_basket")


def test_ajax_add_membership_login_required(client):
    resp = client.get(add_url)
    assert resp.status_code == 302
    assert reverse("account_login") in resp.url


def test_ajax_add_membership_post_required(client, configured_user):
    client.force_login(configured_user)
    resp = client.get(add_url)
    assert resp.status_code == 405


@pytest.mark.freeze_time("2022-3-15")
def test_ajax_add_membership(client, configured_user, membership_type):
    client.force_login(configured_user)
    assert configured_user.memberships.count() == 0
    resp = client.post(
        add_url, {"membership_type_id": membership_type.id, "month": 3, "year": 2022}
    )
    assert resp.status_code == 200
    assert resp.json()["cart_item_menu_count"] == 1
    assert configured_user.memberships.count() == 1
    membership = configured_user.memberships.first()
    assert not membership.paid
    assert membership.month == 3
    assert membership.year == 2022
    assert membership.membership_type == membership_type
