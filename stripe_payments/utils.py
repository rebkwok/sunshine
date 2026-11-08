import logging

import stripe
from django.contrib.sites.models import Site

from activitylog.models import ActivityLog
from booking.email_helpers import send_gift_voucher_email

from .emails import send_invalid_request_email, send_processed_payment_emails
from .exceptions import StripeProcessingError
from .models import Invoice, Seller, StripePaymentIntent, StripeRefund

logger = logging.getLogger(__name__)


def _get_billing_email(payment_intent, stripe_account):
    # A payment intent from a webhook event has the webhook endpoint's API version, so
    # retrieve it to make sure we have the latest_charge
    payment_intent = stripe.PaymentIntent.retrieve(
        payment_intent.id, expand=["latest_charge"], stripe_account=stripe_account
    )
    return payment_intent.latest_charge.billing_details.email


def get_invoice_from_stripe_object(stripe_object, raise_immediately=False):
    # Don't raise exception shere so we don't expose it to the user; leave it for the webhook
    invoice_id = getattr(stripe_object.metadata, "invoice_id", None)
    if not invoice_id:
        #  No invoice id in the metadata is unlikely to be an error; more likely it's a payment not made via the
        # site.
        logger.warning("No invoice ID found for stripe object %s", stripe_object.id)
        return None

    try:
        return Invoice.objects.get(invoice_id=invoice_id)
    except Invoice.DoesNotExist:
        error_msg = f"Error processing stripe object {stripe_object.id}; could not find invoice matching id from metadata '{invoice_id}'"
        logger.error(error_msg)
        if raise_immediately:
            raise StripeProcessingError(error_msg)
    return None


def get_invoice_from_payment_intent(
    payment_intent, stripe_account, raise_immediately=False
):
    invoice = get_invoice_from_stripe_object(payment_intent, raise_immediately)
    if (
        invoice is not None
        and not invoice.username
        and payment_intent.status == "succeeded"
    ):
        # if there's no username on the invoice, it's from a guest checkout
        # Add the username from the billing email
        try:
            billing_email = _get_billing_email(payment_intent, stripe_account)
        except stripe.StripeError as error:
            logger.error(
                "Error retrieving billing email for stripe payment intent %s: %s",
                payment_intent.id,
                error,
            )
            if raise_immediately:
                raise
            return None
        if billing_email:
            invoice.username = billing_email
            # Only update the username; the invoice could have been paid since we got it
            Invoice.objects.filter(pk=invoice.pk).update(username=billing_email)
    return invoice


def check_stripe_data(payment_intent, invoice):
    signature = getattr(payment_intent.metadata, "invoice_signature", None)
    if signature != invoice.signature():
        raise StripeProcessingError(
            f"Could not verify invoice signature: payment intent {payment_intent.id}; invoice id {invoice.invoice_id}"
        )

    if payment_intent.amount != int(invoice.amount * 100):
        raise StripeProcessingError(
            f"Invoice amount is not correct: payment intent {payment_intent.id} ({payment_intent.amount / 100}); "
            f"invoice id {invoice.invoice_id} ({invoice.amount})"
        )


def mark_invoice_paid(invoice, payment_method):
    for booking in invoice.bookings.all():
        booking.paid = True
        booking.save()
    for membership in invoice.memberships.all():
        membership.paid = True
        membership.save()
    for gift_voucher in invoice.gift_vouchers.all():
        gift_voucher.paid = True
        gift_voucher.save()
        gift_voucher.activate()

    invoice.paid = True
    invoice.save()
    ActivityLog.objects.create(
        log=f"Invoice {invoice.invoice_id} (user {invoice.username}) paid by {payment_method}"
    )


def send_invoice_paid_emails(invoice, request=None):
    send_processed_payment_emails(invoice)
    for gift_voucher in invoice.gift_vouchers.all():
        send_gift_voucher_email(gift_voucher, request=request)


def process_refund(request, booking):
    # process refund
    refunded = False
    try:
        try:
            payment_intent = StripePaymentIntent.objects.get(
                payment_intent_id=booking.invoice.stripe_payment_intent_id
            )
        except StripePaymentIntent.DoesNotExist:
            # send warning email to tech support
            send_invalid_request_email(request, booking, "Payment intent not found")
        else:
            seller = Seller.objects.filter(
                site=Site.objects.get_current(request)
            ).first()

            # get the amount to refund from the metadata (in) pence)
            amount = payment_intent.metadata.get(f"booking_{booking.id}_cost_in_p")
            if amount is None:
                # send warning email to tech support
                send_invalid_request_email(
                    request, booking, "Amount could not be parsed from PI metadata"
                )
            else:
                try:
                    refund = stripe.Refund.create(
                        amount=int(amount),
                        metadata={
                            "booking_id": booking.id,
                            "cancelled_by": request.user.email,
                        },
                        payment_intent=payment_intent.payment_intent_id,
                        reason="requested_by_customer",
                        stripe_account=seller.stripe_user_id,
                    )
                    StripeRefund.create_from_refund_obj(
                        refund, payment_intent, booking.id
                    )
                    refunded = True
                    ActivityLog.objects.create(
                        log=f"Refund for booking {booking.id} (user {booking.user.username}) processed"
                    )
                except stripe.error.InvalidRequestError as error:
                    # send warning email to tech support
                    send_invalid_request_email(request, booking, str(error))
    except Exception as error:  # noqa: BLE001
        # catch anything else
        send_invalid_request_email(request, booking, str(error))

    return refunded
