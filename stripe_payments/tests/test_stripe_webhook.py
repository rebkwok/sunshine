from unittest.mock import patch, Mock
import json
import pytest

from django.conf import settings
from django.contrib.sites.models import Site
from django.core import mail
from django.shortcuts import reverse

from model_bakery import baker

from ..models import Seller, StripePaymentIntent


pytestmark = pytest.mark.django_db


# stripe_webhook view
webhook_url = reverse("stripe_payments:stripe_webhook")


@pytest.fixture
def mock_stripe_verify_header():
    with patch("stripe.WebhookSignature.verify_header") as mock_verify:
        mock_verify.return_value = None
        yield mock_verify


@pytest.fixture
def mock_stripe_payload(seller):
    def _mock_stripe_payload(event_type, **params):
        object_data = params or {}
        account = object_data.pop("seller", seller).stripe_user_id
        match event_type:
            case (
                "payment_intent.payment_failed"
                | "payment_intent.requires_action"
                | "payment_intent.succeeded"
            ):
                object = {
                    "id": "mock-intent-id",
                    "object": "payment_intent",
                    "amount": 1000,
                    "currency": "gbp",
                    "status": "succeeded",
                    "description": "",
                    "client_secret": "secret",
                    "charges": {
                        "data": [
                            {"billing_details": {"email": "stripe-payer@test.com"}}
                        ]
                    },
                    **object_data,
                }
            case "payment_intent.refunded":
                object = {
                    "id": "mock-refund-id",
                    "amount": 800,
                    "status": "succeeded",
                    "metadata": {},
                    "currency": "gbp",
                    "reason": "",
                    **object_data,
                }
            case "account.application.authorized" | "account.application.deauthorized":
                object = {"id": "application-id", **object_data}
            case _:
                assert False, f"unhandled event type {event_type}"

        payload = {
            "id": "evt_test123",
            "object": "event",
            "type": event_type,
            "created": 1630000000,
            "data": {"object": object},
            "livemode": False,
            "api_version": "2020-08-27",
            "account": account,
        }
        return payload

    return _mock_stripe_payload


def post_to_webhook(client, payload):
    return client.post(
        webhook_url,
        data=json.dumps(payload),
        content_type="application/json",
        HTTP_STRIPE_SIGNATURE="t=1234,v1=absjfdjfeiof",
    )


def test_webhook_with_matching_invoice_and_membership(
    mock_stripe_verify_header,
    mock_stripe_payload,
    client,
    invoice,
    membership,
    configured_user,
):
    assert StripePaymentIntent.objects.exists() is False
    metadata = {
        "invoice_id": "foo",
        "invoice_signature": invoice.signature(),
        **invoice.items_metadata(),
    }
    payload = mock_stripe_payload("payment_intent.succeeded", metadata=metadata)
    resp = post_to_webhook(client, payload)
    assert resp.status_code == 200
    membership.refresh_from_db()
    invoice.refresh_from_db()

    assert membership.paid is True
    assert invoice.paid is True
    payment_intent_obj = StripePaymentIntent.objects.latest("id")
    assert payment_intent_obj.invoice == invoice

    assert len(mail.outbox) == 2
    assert mail.outbox[0].to == [settings.DEFAULT_STUDIO_EMAIL]
    assert mail.outbox[1].to == [configured_user.email]
    assert "Your payment has been processed" in mail.outbox[1].subject


def test_webhook_with_mismatched_seller(
    mock_stripe_verify_header, mock_stripe_payload, client, invoice
):
    metadata = {
        "invoice_id": "foo",
        "invoice_signature": invoice.signature(),
        **invoice.items_metadata(),
    }
    payload = mock_stripe_payload(
        "payment_intent.succeeded", seller=baker.make(Seller), metadata=metadata
    )
    resp = post_to_webhook(client, payload)
    assert resp.status_code == 200
    assert resp.content.decode() == "Ignored: Mismatched seller account"


def test_webhook_with_no_account_on_event(
    mock_stripe_verify_header, mock_stripe_payload, client, invoice
):
    metadata = {
        "invoice_id": "foo",
        "invoice_signature": invoice.signature(),
        **invoice.items_metadata(),
    }
    payload = mock_stripe_payload("payment_intent.succeeded", metadata=metadata)
    del payload["account"]

    resp = post_to_webhook(client, payload)
    assert resp.status_code == 200
    assert resp.content.decode() == ""


def test_webhook_already_processed(
    mock_stripe_verify_header, mock_stripe_payload, client, invoice, membership
):
    membership.paid = True
    membership.save()
    invoice.paid = True
    invoice.save()
    metadata = {
        "invoice_id": "foo",
        "invoice_signature": invoice.signature(),
        **invoice.items_metadata(),
    }
    payload = mock_stripe_payload("payment_intent.succeeded", metadata=metadata)
    resp = post_to_webhook(client, payload)

    assert resp.status_code == 200
    # already processed, no emails sent
    assert len(mail.outbox) == 0


def test_webhook_with_invalid_payload(mock_stripe_verify_header, client):
    resp = post_to_webhook(client, "foo")
    assert resp.status_code == 400
    assert resp.content.decode() == "Unable to contruct webhook event"


def test_webhook_stripe_verification_error(client, mock_stripe_payload):
    resp = post_to_webhook(client, mock_stripe_payload("payment_intent.succeeded"))
    # stripe verification error returns 400 so stripe will try again
    assert resp.status_code == 400
    assert resp.content.decode() == "Invalid webhook signature"


def test_webhook_exception_no_invoice_signature(
    mock_stripe_verify_header, mock_stripe_payload, client, invoice, membership
):
    # Correct invoice id; no invoice signature
    metadata = {
        "invoice_id": "foo",
        **invoice.items_metadata(),
    }
    payload = mock_stripe_payload("payment_intent.succeeded", metadata=metadata)
    resp = post_to_webhook(client, payload)
    assert resp.status_code == 200

    # invoice and block is still unpaid
    assert membership.paid is False
    assert invoice.paid is False

    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [settings.SUPPORT_EMAIL]
    assert "WARNING: Something went wrong with a payment!" in mail.outbox[0].subject
    assert (
        "Could not verify invoice signature: payment intent mock-intent-id; invoice id foo"
        in mail.outbox[0].body
    )


def test_webhook_exception_invalid_invoice_signature(
    mock_stripe_verify_header, mock_stripe_payload, client, invoice, membership
):
    # Correct invoice id; invalid invoice signature
    metadata = {
        "invoice_id": "foo",
        "invoice_signature": "foo",
        **invoice.items_metadata(),
    }
    payload = mock_stripe_payload("payment_intent.succeeded", metadata=metadata)
    resp = post_to_webhook(client, payload)
    assert resp.status_code == 200

    # invoice and block is still unpaid
    assert membership.paid is False
    assert invoice.paid is False

    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [settings.SUPPORT_EMAIL]
    assert "WARNING: Something went wrong with a payment!" in mail.outbox[0].subject
    assert (
        "Could not verify invoice signature: payment intent mock-intent-id; invoice id foo"
        in mail.outbox[0].body
    )


def test_webhook_exception_retrieving_invoice(
    mock_stripe_verify_header, mock_stripe_payload, client, invoice, membership
):
    # invalid invoice ID
    metadata = {
        "invoice_id": "bar",
        "invoice_signature": invoice.signature(),
        **invoice.items_metadata(),
    }
    payload = mock_stripe_payload("payment_intent.succeeded", metadata=metadata)
    resp = post_to_webhook(client, payload)
    assert resp.status_code == 200

    # invoice and block is still unpaid
    assert membership.paid is False
    assert invoice.paid is False

    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [settings.SUPPORT_EMAIL]
    assert "WARNING: Something went wrong with a payment!" in mail.outbox[0].subject
    assert (
        "Error processing stripe payment intent mock-intent-id; could not find invoice matching id from metadata 'bar'"
        in mail.outbox[0].body
    )


def test_webhook_no_invoice_metadata(
    mock_stripe_verify_header, mock_stripe_payload, client
):
    # no invoice info in metadata; not an error
    payload = mock_stripe_payload("payment_intent.succeeded", metadata={})
    resp = post_to_webhook(client, payload)
    assert resp.status_code == 200
    assert len(mail.outbox) == 0


def test_webhook_refunded(
    mock_stripe_verify_header, mock_stripe_payload, client, invoice, membership
):
    membership.paid = True
    membership.save()
    invoice.paid = True
    invoice.save()
    metadata = {
        "invoice_id": "foo",
        "invoice_signature": invoice.signature(),
        **invoice.items_metadata(),
    }
    payload = mock_stripe_payload("payment_intent.refunded", metadata=metadata)
    resp = post_to_webhook(client, payload)
    assert resp.status_code == 200
    membership.refresh_from_db()
    invoice.refresh_from_db()
    # invoice and block is still paid, we only notify support by email
    assert membership.paid is True
    assert invoice.paid is True

    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [settings.SUPPORT_EMAIL]
    assert "WARNING: Payment refund processed" in mail.outbox[0].subject


def test_webhook_payment_failed_unexpected_error(
    client, mock_stripe_verify_header, mock_stripe_payload, invoice, membership
):
    metadata = {
        "invoice_id": "foo",
        "invoice_signature": invoice.signature(),
        **invoice.items_metadata(),
    }
    payload = mock_stripe_payload(
        "payment_intent.payment_failed",
        metadata=metadata,
        last_payment_error={
            "type": "card_error",
            "code": "card_declined",
            "decline_code": "fraudulent",
        },
    )

    resp = post_to_webhook(client, payload)
    assert resp.status_code == 200
    membership.refresh_from_db()
    invoice.refresh_from_db()
    # invoice and block is still unpaid
    assert membership.paid is False
    assert invoice.paid is False

    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [settings.SUPPORT_EMAIL]
    assert "WARNING: Something went wrong with a payment!" in mail.outbox[0].subject
    assert (
        f"Failed payment intent id: mock-intent-id; invoice id {invoice.invoice_id}; "
        "error: card_error; decline code: fraudulent"
    ) in mail.outbox[0].body


def test_webhook_payment_failed_expected_error(
    client, mock_stripe_verify_header, mock_stripe_payload, invoice, membership
):
    metadata = {
        "invoice_id": "foo",
        "invoice_signature": invoice.signature(),
        **invoice.items_metadata(),
    }
    payload = mock_stripe_payload(
        "payment_intent.payment_failed",
        metadata=metadata,
        last_payment_error={
            "type": "card_error",
            "code": "card_declined",
            "decline_code": "expired_card",
        },
    )

    resp = post_to_webhook(client, payload)
    assert resp.status_code == 200
    membership.refresh_from_db()
    invoice.refresh_from_db()
    # invoice and block is still unpaid
    assert membership.paid is False
    assert invoice.paid is False
    # no emails for expected errors


def test_webhook_payment_requires_action(
    mock_stripe_verify_header, mock_stripe_payload, client, invoice, membership
):
    metadata = {
        "invoice_id": "foo",
        "invoice_signature": invoice.signature(),
        **invoice.items_metadata(),
    }
    payload = mock_stripe_payload("payment_intent.requires_action", metadata=metadata)
    resp = post_to_webhook(client, payload)
    assert resp.status_code == 200
    membership.refresh_from_db()
    invoice.refresh_from_db()
    # invoice and block is still unpaid
    assert membership.paid is False
    assert invoice.paid is False
    # not an error, no emails sent
    assert len(mail.outbox) == 0


@patch("stripe_payments.views.stripe.Account")
def test_webhook_authorized_account(
    mock_account, mock_stripe_verify_header, mock_stripe_payload, client
):
    # mock the seller that should have been created in the StripeAuthorizeCallbackView
    baker.make(Seller, stripe_user_id="stripe-account-1")
    mock_account.list.return_value = Mock(data=[Mock(id="stripe-account-1")])

    payload = mock_stripe_payload("account.application.authorized")
    resp = post_to_webhook(client, payload)
    assert resp.status_code == 200


@patch("stripe_payments.views.stripe.Account")
def test_webhook_authorized_account_no_seller(
    mock_account, mock_stripe_verify_header, mock_stripe_payload, client
):
    mock_account.list.return_value = Mock(data=[Mock(id="stripe-account-1")])

    payload = mock_stripe_payload("account.application.authorized")
    resp = post_to_webhook(client, payload)
    assert resp.status_code == 200
    assert (
        resp.content.decode() == "Stripe account has no associated seller on this site"
    )


@patch("stripe_payments.views.stripe.Account")
def test_webhook_deauthorized_account(
    mock_account, mock_stripe_verify_header, mock_stripe_payload, seller, client
):
    assert seller.site == Site.objects.get_current()
    mock_account.list.return_value = Mock(data=[])

    payload = mock_stripe_payload("account.application.deauthorized")
    resp = post_to_webhook(client, payload)
    assert resp.status_code == 200
    seller.refresh_from_db()
    assert seller.site is None
