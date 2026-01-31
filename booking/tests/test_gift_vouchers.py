# -*- coding: utf-8 -*-
from model_bakery import baker
import pytest
from django.urls import reverse

from booking.models import (
    GiftVoucherType,
    GiftVoucher,
    ItemVoucher,
    TotalVoucher,
)


pytestmark = pytest.mark.django_db

buy_url = reverse("booking:buy_gift_voucher")

# GiftVoucherPurchaseView


def test_gift_voucher_purchase_view_login_not_required(
    client, configured_user, gift_voucher_types
):
    resp = client.get(buy_url)
    assert resp.status_code == 200
    # only active voucher configs shown
    baker.make(GiftVoucherType, discount_amount=11, active=False)
    assert GiftVoucherType.objects.count() == 6
    assert len(resp.context["gift_vouchers_available"]) == 5
    assert sorted([gvt.id for gvt in gift_voucher_types.values()]) == sorted(
        [gvt.id for gvt in resp.context["gift_vouchers_available"]]
    )
    assert "<form" in resp.rendered_content
    assert "Please check your email address is correct" in resp.rendered_content

    client.force_login(configured_user)
    resp = client.get(buy_url)
    # email check warning only shown for not-logged in users
    assert "Please check your email address is correct" not in resp.rendered_content


def test_gift_voucher_purchase_options(client, configured_user, gift_voucher_types):
    baker.make(GiftVoucherType, discount_amount=11, active=False)
    client.force_login(configured_user)
    resp = client.get(buy_url)
    form = resp.context_data["form"]
    assert [config.id for config in form.fields["gift_voucher_type"].queryset] == [
        gvt.id for gvt in resp.context["gift_vouchers_available"]
    ]
    assert form.fields["user_email"].initial == configured_user.email


def test_gift_voucher_purchase(client, configured_user, gift_voucher_types):
    client.force_login(configured_user)
    assert GiftVoucher.objects.exists() is False
    data = {
        "gift_voucher_type": gift_voucher_types["membership_2"].id,
        "user_email": configured_user.email,
        "user_email1": configured_user.email,
        "recipient_name": "Donald Duck",
        "message": "Happy Birthday",
    }
    client.post(buy_url, data)
    assert GiftVoucher.objects.exists() is True
    gift_voucher = GiftVoucher.objects.first()
    assert not gift_voucher.paid
    assert isinstance(gift_voucher.voucher, ItemVoucher)
    assert gift_voucher.voucher.purchaser_email == configured_user.email
    assert gift_voucher.voucher.name == "Donald Duck"
    assert gift_voucher.voucher.message == "Happy Birthday"


def test_gift_voucher_purchase_mismatched_emails(client, gift_voucher_types):
    assert GiftVoucher.objects.exists() is False
    data = {
        "gift_voucher_type": gift_voucher_types["membership_2"].id,
        "user_email": "test@test.com",
        "user_email1": "test1@test.com",
        "recipient_name": "Donald Duck",
        "message": "Happy Birthday",
    }
    resp = client.post(buy_url, data)
    form = resp.context_data["form"]
    assert form.is_valid() is False
    assert form.errors == {"user_email1": ["Email addresses do not match"]}


def test_gift_voucher_purchase_no_login(client, gift_voucher_types):
    assert "purchases" not in client.session
    assert GiftVoucher.objects.exists() is False
    data = {
        "gift_voucher_type": gift_voucher_types["membership_2"].id,
        "user_email": "unknown@test.com",
        "user_email1": "unknown@test.com",
    }
    resp = client.post(buy_url, data)
    assert GiftVoucher.objects.exists()
    gift_voucher = GiftVoucher.objects.first()
    assert gift_voucher.paid is False
    assert gift_voucher.voucher.purchaser_email == "unknown@test.com"

    assert resp.url == reverse("booking:guest_shopping_basket")
    assert client.session["purchases"] == {"gift_vouchers": [gift_voucher.id]}


# GiftVoucherUpdateView


def update_url(gift_voucher):
    return reverse("booking:gift_voucher_update", args=(gift_voucher.slug,))


def test_gift_voucher_update_login_not_required(client, membership_gift_voucher):
    """
    test that purchase update form is shown if not logged in
    """
    resp = client.get(update_url(membership_gift_voucher))
    assert resp.status_code == 200
    assert "<form" in resp.rendered_content


def test_gift_voucher_purchase_options_disabled_for_activated_voucher(
    client, membership_gift_voucher
):
    resp = client.get(update_url(membership_gift_voucher))
    form = resp.context_data["form"]
    assert form.fields["gift_voucher_type"].disabled is False

    membership_gift_voucher.activate()
    resp = client.get(update_url(membership_gift_voucher))
    form = resp.context_data["form"]
    assert form.fields["gift_voucher_type"].disabled is True


def test_gift_voucher_change_type(
    client, configured_user, gift_voucher_types, membership_gift_voucher
):
    client.force_login(configured_user)
    assert isinstance(membership_gift_voucher.voucher, ItemVoucher)
    assert TotalVoucher.objects.exists() is False
    data = {
        "gift_voucher_type": gift_voucher_types["total"].id,
        "user_email": configured_user.email,
        "user_email1": configured_user.email,
        "recipient_name": "Donald Duck",
        "message": "Happy Birthday",
    }
    client.post(update_url(membership_gift_voucher), data)
    membership_gift_voucher.refresh_from_db()
    assert isinstance(membership_gift_voucher.voucher, TotalVoucher)
    assert ItemVoucher.objects.exists() is False

    data.update({"gift_voucher_type": gift_voucher_types["regular_session"].id})
    resp = client.post(update_url(membership_gift_voucher), data)
    membership_gift_voucher.refresh_from_db()
    assert isinstance(membership_gift_voucher.voucher, ItemVoucher)
    assert membership_gift_voucher.voucher.event_types == ["regular_session"]
    assert TotalVoucher.objects.exists() is False
    assert resp.url == reverse("booking:shopping_basket")


def test_gift_voucher_change_anon_user(client):
    voucher = baker.make_recipe(
        "booking.gift_voucher_10",
        paid=False,
        total_voucher__purchaser_email="anon@test.com",
    )
    data = {
        "gift_voucher_type": voucher.gift_voucher_type.id,
        "user_email": "anon@test.com",
        "user_email1": "anon@test.com",
        "recipient_name": "Donald Duck",
        "message": "Happy Birthday",
    }
    resp = client.post(update_url(voucher), data)
    voucher.refresh_from_db()
    assert voucher.voucher.purchaser_email == "anon@test.com"
    assert voucher.voucher.name == "Donald Duck"
    assert resp.url == reverse("booking:guest_shopping_basket")


def test_gift_voucher_update_paid_voucher(
    client, configured_user, membership_gift_voucher
):
    membership_gift_voucher.paid = True
    membership_gift_voucher.save()
    data = {
        "gift_voucher_type": membership_gift_voucher.gift_voucher_type.id,
        "user_email": configured_user.email,
        "user_email1": configured_user.email,
        "recipient_name": "Mickey Mouse",
        "message": "Happy Birthday",
    }
    resp = client.post(update_url(membership_gift_voucher), data)
    membership_gift_voucher.refresh_from_db()
    assert membership_gift_voucher.voucher.name == "Mickey Mouse"
    assert resp.url == reverse(
        "booking:gift_voucher_details", args=(membership_gift_voucher.slug,)
    )


# GiftVoucherDetailView


def detail_url(voucher):
    return reverse("booking:gift_voucher_details", args=(voucher.slug,))


def test_gift_voucher_detail_login_not_required(client, membership_gift_voucher):
    resp = client.get(detail_url(membership_gift_voucher))
    assert resp.status_code == 200


def test_voucher_instructions(
    client, membership_gift_voucher, total_gift_voucher, event_gift_voucher
):
    resp = client.get(detail_url(membership_gift_voucher))
    assert "Go to Memberships and select" in resp.rendered_content
    assert "Go to Book and add items to shopping basket" not in resp.rendered_content
    assert (
        "Go to Memberships or Book to add items to shopping basket"
        not in resp.rendered_content
    )

    resp = client.get(detail_url(event_gift_voucher))
    assert "Go to Book and add items to shopping basket" in resp.rendered_content
    assert "Go to Memberships and select" not in resp.rendered_content
    assert (
        "Go to Memberships or Book to add items to shopping basket"
        not in resp.rendered_content
    )

    resp = client.get(detail_url(total_gift_voucher))
    assert (
        "Go to Memberships or Book to add items to shopping basket"
        in resp.rendered_content
    )
    assert "Go to Book and add items to shopping basket" not in resp.rendered_content
    assert "Go to Memberships and select" not in resp.rendered_content


# voucher_details view


def test_voucher_details_view_login_not_required(client):
    voucher = baker.make(TotalVoucher, discount_amount=10)
    resp = client.get(reverse("booking:voucher_details", args=(voucher.code,)))
    assert resp.status_code == 200
    assert resp.context["voucher"] == voucher


def test_voucher_details_view_gift_voucher_redirect(client, membership_gift_voucher):
    resp = client.get(
        reverse("booking:voucher_details", args=(membership_gift_voucher.code,))
    )
    assert resp.status_code == 302
    assert resp.url == reverse(
        "booking:gift_voucher_details", args=(membership_gift_voucher.slug,)
    )
