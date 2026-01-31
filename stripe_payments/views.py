import json
import logging

import stripe

from django.conf import settings
from django.contrib.sites.models import Site
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.shortcuts import render, HttpResponse

from activitylog.models import ActivityLog
from .emails import send_failed_payment_emails, send_processed_refund_emails
from .exceptions import StripeProcessingError
from .models import Seller, StripePaymentIntent
from .utils import (
    get_invoice_from_payment_intent,
    check_stripe_data,
    process_invoice_items,
)

logger = logging.getLogger(__name__)


def _process_completed_stripe_payment(
    payment_intent, invoice, seller=None, request=None
):
    if not invoice.paid:
        logger.info("Updating items to paid for invoice %s", invoice.invoice_id)
        check_stripe_data(payment_intent, invoice)
        logger.info("Stripe check OK")
        process_invoice_items(invoice, payment_method="Stripe", request=request)
        # update/create the django model PaymentIntent - this is just for records
        StripePaymentIntent.update_or_create_payment_intent_instance(
            payment_intent, invoice, seller
        )
    else:
        logger.info(
            "Payment Intents signal received for invoice %s; already processed",
            invoice.invoice_id,
        )


@require_POST
def stripe_payment_complete(request):
    payload = request.POST.get("payload")
    if payload is None:
        logger.error("No payload found %s", payload)
        send_failed_payment_emails(
            payment_intent=None, error=f"POST: {str(request.POST)}"
        )
        return render(request, "stripe_payments/non_valid_payment.html")

    payload = json.loads(payload)
    logger.info("Processing payment intent from payload %s", payload)
    stripe.api_key = settings.STRIPE_SECRET_KEY
    seller = Seller.objects.filter(site=Site.objects.get_current(request)).first()
    stripe_account = seller.stripe_user_id
    payment_intent = stripe.PaymentIntent.retrieve(
        payload["id"], stripe_account=stripe_account
    )
    failed = False

    if payment_intent.status == "succeeded":
        invoice = get_invoice_from_payment_intent(
            payment_intent, raise_immediately=False
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
    payment_intent.metadata.pop("invoice_id", None)
    payment_intent.metadata.pop("invoice_signature", None)
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
    stripe.api_key = settings.STRIPE_SECRET_KEY
    payload = request.body
    sig_header = request.META["HTTP_STRIPE_SIGNATURE"]

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_ENDPOINT_SECRET
        )
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        logger.error(e)
        return HttpResponse("Invalid webhook signature", status=400)
    except Exception as e:
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

    try:
        site_seller = Seller.objects.filter(
            site=Site.objects.get_current(request)
        ).first()
        try:
            # account is only present on the event if it originated from a connected account
            # All events we're interested in are related to a connected account, but potentially
            # a refund or other event that occurred outside of the system could be relevant, so
            # if this raises an AttributeError, we log and proceed
            account = event.account
        except Exception as e:
            logger.error(e)
        else:
            if account != site_seller.stripe_user_id:
                # relates to a different seller, just return and let the next webhook manage it
                logger.info("Mismatched seller account %s", account)
                return HttpResponse("Ignored: Mismatched seller account", status=200)

        payment_intent = event_object
        invoice = get_invoice_from_payment_intent(
            payment_intent, raise_immediately=True
        )
        # invoice can be None; this means there was no invoice info in the payment intent
        # metadata, which isn't an error; it's probably a transaction that happened outside
        # of the system. If we got invoice info but couldn't find a matching invoice, this IS
        # raised as an exception and will be handles bellow
        # payment_failed and requires_action happend when a user does something wrong - either
        # their card is declined, has insufficient funds etc. There's no error in the system,
        # so just log it and continue
        # https://docs.stripe.com/declines/codes
        # The following are unusual and not the standard user/card error (entering the wrong
        # cvv, insufficient funds etc) and might need more investigation
        unexpected_decline_codes = [
            "authentication_not_handled",
            "approve_with_id",
            "fraudulent",
            "invalid_amount",
            "merchant_blacklist",
            "processing_error",
            "reenter_transaction",
            "testmode_decline",
        ]
        if invoice is not None:
            if event.type == "payment_intent.succeeded":
                _process_completed_stripe_payment(
                    payment_intent, invoice, request=request
                )
            elif event.type == "payment_intent.refunded":
                send_processed_refund_emails(invoice)
            elif event.type == "payment_intent.payment_failed":
                msg = (
                    f"Failed payment intent id: {payment_intent.id}; invoice id {invoice.invoice_id}; "
                    f"error: {payment_intent.last_payment_error.type}; decline code: {payment_intent.last_payment_error.decline_code}"
                )
                if (
                    payment_intent.last_payment_error.decline_code
                    in unexpected_decline_codes
                ):
                    logger.error(msg)
                    send_failed_payment_emails(error=msg)
                else:
                    logger.info(msg)
            elif event.type == "payment_intent.requires_action":
                logger.info(
                    f"Payment intent requires action: id {payment_intent.id}; invoice id {invoice.invoice_id}"
                )
    except Exception as e:  # log anything else and send error emails
        logger.error(e)
        send_failed_payment_emails(error=e)
    return HttpResponse(status=200)
