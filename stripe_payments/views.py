import json
import logging

import stripe
from django.conf import settings
from django.contrib.sites.models import Site
from django.db import transaction
from django.shortcuts import HttpResponse, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from activitylog.models import ActivityLog

from .emails import send_failed_payment_emails, send_processed_refund_emails
from .exceptions import StripeProcessingError
from .models import Invoice, Seller, StripePaymentIntent
from .utils import (
    check_stripe_data,
    get_invoice_from_payment_intent,
    get_invoice_from_stripe_object,
    mark_invoice_paid,
    send_invoice_paid_emails,
)

logger = logging.getLogger(__name__)

HANDLED_EVENT_TYPES = {
    "charge.refunded",
    "payment_intent.payment_failed",
    "payment_intent.requires_action",
    "payment_intent.succeeded",
}

# The following are unusual and not the standard user/card error (entering the wrong
# cvv, insufficient funds etc) and might need more investigation
UNEXPECTED_DECLINE_CODES = [
    "authentication_not_handled",
    "approve_with_id",
    "fraudulent",
    "invalid_amount",
    "merchant_blacklist",
    "processing_error",
    "reenter_transaction",
    "testmode_decline",
]


def _process_completed_stripe_payment(
    payment_intent, invoice, seller=None, request=None
):
    # This can run for the same payment from the browser and the webhook at the same
    # time, so lock the invoice to check and update it
    with transaction.atomic():
        invoice = Invoice.objects.select_for_update().get(pk=invoice.pk)
        if invoice.paid:
            logger.info(
                "Payment Intents signal received for invoice %s; already processed",
                invoice.invoice_id,
            )
            return
        logger.info("Updating items to paid for invoice %s", invoice.invoice_id)
        check_stripe_data(payment_intent, invoice)
        logger.info("Stripe check OK")
        mark_invoice_paid(invoice, payment_method="Stripe")
        # update/create the django model PaymentIntent - this is just for records
        StripePaymentIntent.update_or_create_payment_intent_instance(
            payment_intent, invoice, seller
        )

    try:
        send_invoice_paid_emails(invoice, request=request)
    except Exception:
        # The payment has been processed, so a failed email shouldn't fail it or cause a
        # retry, which wouldn't send the emails again
        logger.exception("Error sending emails for invoice %s", invoice.invoice_id)


def _process_payment_intent_event(event, seller, request):
    payment_intent = event.data.object
    invoice = get_invoice_from_payment_intent(
        payment_intent, seller.stripe_user_id, raise_immediately=True
    )
    # invoice can be None; this means there was no invoice info in the payment intent
    # metadata, which isn't an error; it's probably a transaction that happened outside
    # of the system. If we got invoice info but couldn't find a matching invoice, this IS
    # raised as an exception and will be handles bellow
    if invoice is None:
        return

    if event.type == "payment_intent.succeeded":
        _process_completed_stripe_payment(payment_intent, invoice, request=request)
    elif event.type == "payment_intent.payment_failed":
        # payment_failed and requires_action happend when a user does something wrong - either
        # their card is declined, has insufficient funds etc. There's no error in the system,
        # so just log it and continue
        # https://docs.stripe.com/declines/codes
        # There's no decline code on some failures, e.g. failed 3DS authentication
        decline_code = getattr(payment_intent.last_payment_error, "decline_code", None)
        msg = (
            f"Failed payment intent id: {payment_intent.id}; invoice id {invoice.invoice_id}; "
            f"error: {payment_intent.last_payment_error.type}; decline code: {decline_code}"
        )
        if decline_code in UNEXPECTED_DECLINE_CODES:
            logger.error(msg)
            send_failed_payment_emails(error=msg)
        else:
            logger.info(msg)
    elif event.type == "payment_intent.requires_action":
        logger.info(
            f"Payment intent requires action: id {payment_intent.id}; invoice id {invoice.invoice_id}"
        )


@require_POST
def stripe_payment_complete(request):
    payload = request.POST.get("payload")
    if payload is None:
        logger.error("No payload found %s", payload)
        send_failed_payment_emails(payment_intent=None, error=f"POST: {request.POST!s}")
        return render(request, "stripe_payments/non_valid_payment.html")

    payload = json.loads(payload)
    logger.info("Processing payment intent from payload %s", payload)
    seller = Seller.objects.filter(site=Site.objects.get_current(request)).first()
    if seller is None:
        error = f"No seller found for payment intent {payload['id']}"
        logger.error(error)
        send_failed_payment_emails(payment_intent=None, error=error)
        return render(request, "stripe_payments/non_valid_payment.html")

    stripe_account = seller.stripe_user_id
    try:
        payment_intent = stripe.PaymentIntent.retrieve(
            payload["id"], stripe_account=stripe_account
        )
    except stripe.StripeError as e:
        error = f"Error retrieving payment intent {payload['id']}: {e}"
        logger.error(error)
        send_failed_payment_emails(payment_intent=None, error=error)
        return render(request, "stripe_payments/non_valid_payment.html")

    failed = False

    if payment_intent.status == "succeeded":
        invoice = get_invoice_from_payment_intent(
            payment_intent, stripe_account, raise_immediately=False
        )
        if invoice is not None:
            try:
                _process_completed_stripe_payment(
                    payment_intent, invoice, seller, request=request
                )
            except StripeProcessingError as e:
                error = f"Error processing Stripe payment: {e}"
                logger.error(e)
                failed = True
        else:
            # No invoice retrieved, fail
            failed = True
            error = f"No invoice could be retrieved from succeeded payment intent {payment_intent.id}"
            logger.error(error)
    else:
        failed = True
        error = f"Payment intent id {payment_intent.id} status: {payment_intent.status}"
        logger.error(error)

    if not failed:
        context = {
            "cart_items": invoice.items_dict().values(),
            "item_types": invoice.item_types(),
            "total_charged": invoice.amount,
        }
        if "total_voucher_code" in request.session:
            del request.session["total_voucher_code"]
        context.update({"total_voucher_code": invoice.total_voucher_code})

        return render(request, "stripe_payments/valid_payment.html", context)
    else:
        send_failed_payment_emails(payment_intent=payment_intent, error=error)
        return render(request, "stripe_payments/non_valid_payment.html")


@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.headers.get("Stripe-Signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_ENDPOINT_SECRET
        )
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        logger.error(e)
        return HttpResponse("Invalid webhook signature", status=400)
    except Exception as e:  # noqa: BLE001
        # Invalid payload
        logger.error(e)
        return HttpResponse("Unable to contruct webhook event", status=400)

    event_object = event.data.object
    if event.type == "account.application.authorized":
        connected_accounts = stripe.Account.list().data
        for connected_account in connected_accounts:
            seller = Seller.objects.filter(stripe_user_id=connected_account.id)
            if not seller.exists():
                logger.error(
                    "Stripe account has no associated seller on this site %s",
                    connected_account.id,
                )
                # return 200 so we don't keep trying. The error log will trigger an email to support.
                return HttpResponse(
                    "Stripe account has no associated seller on this site", status=200
                )
        return HttpResponse(status=200)

    elif event.type == "account.application.deauthorized":
        connected_accounts = stripe.Account.list().data
        connected_account_ids = [account.id for account in connected_accounts]
        for seller in Seller.objects.all():
            if seller.stripe_user_id not in connected_account_ids:
                seller.site = None
                seller.save()
                logger.info("Stripe account disconnected: %s", seller.stripe_user_id)
                ActivityLog.objects.create(
                    log=f"Stripe account disconnected: {seller.stripe_user_id}"
                )
        return HttpResponse(status=200)

    if event.type not in HANDLED_EVENT_TYPES:
        return HttpResponse(status=200)

    try:
        site_seller = Seller.objects.filter(
            site=Site.objects.get_current(request)
        ).first()
        if site_seller is None:
            logger.warning("Stripe event %s ignored: no seller", event.id)
            return HttpResponse("Ignored: No seller", status=200)

        # account is only present on the event if it originated from a connected account
        account = getattr(event, "account", None)
        if account != site_seller.stripe_user_id:
            # relates to a different seller, just return and let the next webhook manage it
            logger.info("Mismatched seller account %s", account)
            return HttpResponse("Ignored: Mismatched seller account", status=200)

        if event.type == "charge.refunded":
            invoice = get_invoice_from_stripe_object(
                event_object, raise_immediately=True
            )
            if invoice is not None:
                send_processed_refund_emails(invoice)
        else:
            _process_payment_intent_event(event, site_seller, request)
    except StripeProcessingError as e:
        # A retry won't fix this, so log it and send error emails, and return 200
        logger.error(e)
        send_failed_payment_emails(error=e)
    except Exception as e:  # noqa: BLE001
        # log anything else and send error emails, and return an error so Stripe retries
        logger.error(e)
        send_failed_payment_emails(error=e)
        return HttpResponse(status=500)
    return HttpResponse(status=200)
