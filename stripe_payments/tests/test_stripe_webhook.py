import json
import time
from unittest.mock import Mock, patch

import pytest
import stripe
from django.conf import settings
from django.contrib.sites.models import Site
from django.core import mail
from django.shortcuts import reverse
from model_bakery import baker

from activitylog.models import ActivityLog
from conftest import get_mock_payment_intent

from ..models import Invoice, Seller, StripePaymentIntent
from ..utils import get_invoice_from_payment_intent
from ..views import _process_completed_stripe_payment

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
                "payment_intent.created"
                | "payment_intent.payment_failed"
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
                    "latest_charge": "mock-charge-id",
                    **object_data,
                }
            case "charge.refunded":
                object = {
                    "id": "mock-charge-id",
                    "object": "charge",
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
    assert resp.content.decode() == "Ignored: Mismatched seller account"
    invoice.refresh_from_db()
    assert invoice.paid is False
    assert len(mail.outbox) == 0


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


def test_webhook_no_signature_header(client):
    resp = client.post(webhook_url, data="{}", content_type="application/json")
    assert resp.status_code == 400
    assert resp.content.decode() == "Invalid webhook signature"


def test_webhook_no_seller(
    mock_stripe_verify_header, mock_stripe_payload, client, invoice
):
    payload = mock_stripe_payload(
        "payment_intent.succeeded", metadata=_invoice_metadata(invoice)
    )
    Seller.objects.all().delete()
    resp = post_to_webhook(client, payload)
    assert resp.status_code == 200
    assert resp.content.decode() == "Ignored: No seller"
    invoice.refresh_from_db()
    assert invoice.paid is False
    assert len(mail.outbox) == 0


def test_webhook_ignores_unhandled_event_types(
    mock_stripe_verify_header, mock_stripe_payload, client
):
    payload = mock_stripe_payload("payment_intent.created")
    payload["type"] = "balance.available"
    # not all objects have metadata
    assert "metadata" not in payload["data"]["object"]
    resp = post_to_webhook(client, payload)
    assert resp.status_code == 200
    assert len(mail.outbox) == 0


def test_webhook_unexpected_error_returns_500_and_can_be_retried(
    mock_stripe_verify_header, mock_stripe_payload, client, invoice, membership
):
    payload = mock_stripe_payload(
        "payment_intent.succeeded", metadata=_invoice_metadata(invoice)
    )
    with patch(
        "stripe_payments.views.StripePaymentIntent.update_or_create_payment_intent_instance",
        side_effect=Exception("database error"),
    ):
        resp = post_to_webhook(client, payload)
    assert resp.status_code == 500
    assert mail.outbox[0].to == [settings.SUPPORT_EMAIL]
    assert "database error" in mail.outbox[0].body
    # the changes are rolled back
    invoice.refresh_from_db()
    membership.refresh_from_db()
    assert invoice.paid is False
    assert membership.paid is False

    resp = post_to_webhook(client, payload)
    assert resp.status_code == 200
    invoice.refresh_from_db()
    membership.refresh_from_db()
    assert invoice.paid is True
    assert membership.paid is True
    assert StripePaymentIntent.objects.filter(invoice=invoice).exists()


def test_webhook_error_sending_emails_does_not_fail_payment(
    mock_stripe_verify_header, mock_stripe_payload, client, invoice, membership
):
    payload = mock_stripe_payload(
        "payment_intent.succeeded", metadata=_invoice_metadata(invoice)
    )
    with patch(
        "stripe_payments.utils.send_processed_payment_emails",
        side_effect=Exception("mail error"),
    ):
        resp = post_to_webhook(client, payload)
    assert resp.status_code == 200
    invoice.refresh_from_db()
    assert invoice.paid is True
    assert StripePaymentIntent.objects.filter(invoice=invoice).exists()
    assert ActivityLog.objects.filter(log__contains="paid by Stripe").exists()


def test_process_completed_payment_checks_paid_on_locked_invoice(invoice):
    # The invoice was paid by another process after this one retrieved it
    stale_invoice = Invoice.objects.get(pk=invoice.pk)
    Invoice.objects.filter(pk=invoice.pk).update(paid=True)

    _process_completed_stripe_payment(get_mock_payment_intent(), stale_invoice)

    assert not StripePaymentIntent.objects.exists()
    assert len(mail.outbox) == 0


def test_guest_username_update_does_not_overwrite_paid(guest_invoice):
    metadata = {"invoice_id": guest_invoice.invoice_id}

    def paid_by_another_process(payment_intent, stripe_account):
        Invoice.objects.filter(pk=guest_invoice.pk).update(paid=True)
        return "stripe-payer@test.com"

    with patch("stripe_payments.utils._get_billing_email", paid_by_another_process):
        invoice = get_invoice_from_payment_intent(
            get_mock_payment_intent(metadata=metadata), "id123"
        )

    assert invoice.username == "stripe-payer@test.com"
    guest_invoice.refresh_from_db()
    assert guest_invoice.username == "stripe-payer@test.com"
    assert guest_invoice.paid is True


def _signature(payload, secret):
    timestamp = int(time.time())
    signature = stripe.WebhookSignature._compute_signature(
        f"{timestamp}.{payload}", secret
    )
    return f"t={timestamp},v1={signature}"


@pytest.mark.parametrize("secret", ["whsec_old", "whsec_new"])
def test_webhook_accepts_each_endpoint_secret(
    client, mock_stripe_payload, invoice, settings, secret
):
    settings.STRIPE_ENDPOINT_SECRETS = ["whsec_old", "whsec_new"]
    payload = json.dumps(
        mock_stripe_payload(
            "payment_intent.succeeded", metadata=_invoice_metadata(invoice)
        )
    )
    resp = client.post(
        webhook_url,
        data=payload,
        content_type="application/json",
        HTTP_STRIPE_SIGNATURE=_signature(payload, secret),
    )
    assert resp.status_code == 200
    invoice.refresh_from_db()
    assert invoice.paid is True


def test_webhook_rejects_other_secret(client, mock_stripe_payload, invoice, settings):
    settings.STRIPE_ENDPOINT_SECRETS = ["whsec_old", "whsec_new"]
    payload = json.dumps(
        mock_stripe_payload(
            "payment_intent.succeeded", metadata=_invoice_metadata(invoice)
        )
    )
    resp = client.post(
        webhook_url,
        data=payload,
        content_type="application/json",
        HTTP_STRIPE_SIGNATURE=_signature(payload, "whsec_other"),
    )
    assert resp.status_code == 400
    assert resp.content.decode() == "Invalid webhook signature"
    invoice.refresh_from_db()
    assert invoice.paid is False


@pytest.mark.parametrize(
    "event_version,processed_version,status_code,content,paid",
    [
        # before switching to the new endpoint
        ("2020-08-27", "2020-08-27", 200, "", True),
        ("2026-09-30.endive", "2020-08-27", 200, "Ignored: newer API version", False),
        # after switching to the new endpoint
        ("2026-09-30.endive", "2026-09-30.endive", 200, "", True),
        ("2020-08-27", "2026-09-30.endive", 400, "Ignored: older API version", False),
    ],
)
def test_webhook_only_processes_configured_api_version(
    mock_stripe_verify_header,
    mock_stripe_payload,
    client,
    invoice,
    settings,
    event_version,
    processed_version,
    status_code,
    content,
    paid,
):
    settings.STRIPE_WEBHOOK_API_VERSION = processed_version
    payload = mock_stripe_payload(
        "payment_intent.succeeded", metadata=_invoice_metadata(invoice)
    )
    payload["api_version"] = event_version
    resp = post_to_webhook(client, payload)
    assert resp.status_code == status_code
    assert resp.content.decode() == content
    invoice.refresh_from_db()
    assert invoice.paid is paid


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
        "Error processing stripe object mock-intent-id; could not find invoice matching id from metadata 'bar'"
        in mail.outbox[0].body
    )


def test_webhook_no_invoice_metadata(
    mock_stripe_verify_header, mock_stripe_payload, client
):
    # no invoice info in metadata; not an error
    payload = mock_stripe_payload("payment_intent.succeeded", metadata={})
    resp = post_to_webhook(client, payload)
    assert resp.status_code == 200
    assert len(mail.outbox) == 0, mail.outbox[0].body


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
    payload = mock_stripe_payload("charge.refunded", metadata=metadata)
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


def test_webhook_refunded_no_invoice_metadata(
    mock_stripe_verify_header, mock_stripe_payload, client
):
    payload = mock_stripe_payload("charge.refunded", metadata={})
    resp = post_to_webhook(client, payload)
    assert resp.status_code == 200
    assert len(mail.outbox) == 0


def test_webhook_payment_failed_no_decline_code(
    client, mock_stripe_verify_header, mock_stripe_payload, invoice
):
    # e.g. failed 3DS authentication
    payload = mock_stripe_payload(
        "payment_intent.payment_failed",
        metadata=_invoice_metadata(invoice),
        last_payment_error={
            "type": "invalid_request_error",
            "code": "payment_intent_authentication_failure",
        },
    )
    resp = post_to_webhook(client, payload)
    assert resp.status_code == 200
    invoice.refresh_from_db()
    assert invoice.paid is False
    assert len(mail.outbox) == 0


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


@pytest.fixture
def guest_invoice():
    yield baker.make(
        Invoice,
        invoice_id="foo",
        amount=10,
        username="",
        stripe_payment_intent_id="mock-intent-id",
    )


def _invoice_metadata(invoice):
    return {
        "invoice_id": invoice.invoice_id,
        "invoice_signature": invoice.signature(),
        **invoice.items_metadata(),
    }


def test_webhook_guest_invoice_username_from_billing_email(
    mock_stripe_verify_header,
    mock_stripe_payload,
    client,
    guest_invoice,
    seller,
):
    retrieved_payment_intent = get_mock_payment_intent()
    payload = mock_stripe_payload(
        "payment_intent.succeeded", metadata=_invoice_metadata(guest_invoice)
    )
    with patch(
        "stripe_payments.utils.stripe.PaymentIntent", autospec=stripe.PaymentIntent
    ) as mock_payment_intent:
        mock_payment_intent.retrieve.return_value = retrieved_payment_intent
        resp = post_to_webhook(client, payload)
    assert resp.status_code == 200
    mock_payment_intent.retrieve.assert_called_once_with(
        "mock-intent-id",
        expand=["latest_charge"],
        stripe_account=seller.stripe_user_id,
    )
    guest_invoice.refresh_from_db()
    assert guest_invoice.username == "stripe-payer@test.com"
    assert guest_invoice.paid is True


def test_webhook_guest_invoice_old_api_version_payload(
    mock_stripe_verify_header, mock_stripe_payload, client, guest_invoice
):
    # The webhook endpoint's API version can be older than the SDK's; events on versions
    # before 2022-11-15 have charges instead of latest_charge
    retrieved_payment_intent = get_mock_payment_intent()
    payload = mock_stripe_payload(
        "payment_intent.succeeded", metadata=_invoice_metadata(guest_invoice)
    )
    del payload["data"]["object"]["latest_charge"]
    payload["data"]["object"]["charges"] = {
        "data": [{"billing_details": {"email": "old-payload@test.com"}}]
    }
    with patch(
        "stripe_payments.utils.stripe.PaymentIntent", autospec=stripe.PaymentIntent
    ) as mock_payment_intent:
        mock_payment_intent.retrieve.return_value = retrieved_payment_intent
        resp = post_to_webhook(client, payload)
    assert resp.status_code == 200
    guest_invoice.refresh_from_db()
    assert guest_invoice.username == "stripe-payer@test.com"
    assert guest_invoice.paid is True


@pytest.mark.parametrize(
    "event_type,status",
    [
        ("payment_intent.created", "requires_payment_method"),
        ("payment_intent.requires_action", "requires_action"),
    ],
)
@patch("stripe_payments.utils.stripe.PaymentIntent", autospec=stripe.PaymentIntent)
def test_webhook_guest_invoice_payment_not_succeeded(
    mock_payment_intent,
    mock_stripe_verify_header,
    mock_stripe_payload,
    client,
    guest_invoice,
    event_type,
    status,
):
    payload = mock_stripe_payload(
        event_type, metadata=_invoice_metadata(guest_invoice), status=status
    )
    # no charge exists yet
    del payload["data"]["object"]["latest_charge"]
    payload["data"]["object"]["charges"] = {"data": []}
    resp = post_to_webhook(client, payload)
    assert resp.status_code == 200
    mock_payment_intent.retrieve.assert_not_called()
    guest_invoice.refresh_from_db()
    assert guest_invoice.username == ""
    assert len(mail.outbox) == 0


@patch("stripe_payments.utils.stripe.PaymentIntent", autospec=stripe.PaymentIntent)
def test_webhook_guest_invoice_error_retrieving_billing_email(
    mock_payment_intent,
    mock_stripe_verify_header,
    mock_stripe_payload,
    client,
    guest_invoice,
):
    mock_payment_intent.retrieve.side_effect = stripe.APIConnectionError("no network")
    payload = mock_stripe_payload(
        "payment_intent.succeeded", metadata=_invoice_metadata(guest_invoice)
    )
    resp = post_to_webhook(client, payload)
    # returns an error so Stripe retries
    assert resp.status_code == 500
    guest_invoice.refresh_from_db()
    assert guest_invoice.paid is False
    assert mail.outbox[0].to == [settings.SUPPORT_EMAIL]
    assert "no network" in mail.outbox[0].body


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
