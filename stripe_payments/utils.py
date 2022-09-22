import logging
from django.urls import reverse

from activitylog.models import ActivityLog
from .emails import send_processed_payment_emails
from .exceptions import StripeProcessingError
from .models import Invoice


logger = logging.getLogger(__name__)


def get_invoice_from_payment_intent(payment_intent, raise_immediately=False):
    # Don't raise the exception here so we don't expose it to the user; leave it for the webhook
    invoice_id = payment_intent.metadata.get("invoice_id")
    if not invoice_id:
        if raise_immediately:
            raise StripeProcessingError(f"Error processing stripe payment intent {payment_intent.id}; no invoice id")
        return None
    try:
        invoice = Invoice.objects.get(invoice_id=invoice_id)
        if not invoice.username:
            # if there's no username on the invoice, it's from a guest checkout
            # Add the username from the billing email
            billing_email = payment_intent.charges.data[0]["billing_details"]["email"]
            invoice.username = billing_email
            invoice.save()
        return invoice
    except Invoice.DoesNotExist:
        logger.error("Error processing stripe payment intent %s; could not find invoice", payment_intent.id)
        if raise_immediately:
            raise StripeProcessingError(f"Error processing stripe payment intent {payment_intent.id}; could not find invoice")
        return None


def check_stripe_data(payment_intent, invoice):
    signature = payment_intent.metadata.get("invoice_signature")
    if signature != invoice.signature():
        raise StripeProcessingError(
            f"Could not verify invoice signature: payment intent {payment_intent.id}; invoice id {invoice.invoice_id}")

    if payment_intent.amount != int(invoice.amount * 100):
        raise StripeProcessingError(
            f"Invoice amount is not correct: payment intent {payment_intent.id} ({payment_intent.amount/100}); "
            f"invoice id {invoice.invoice_id} ({invoice.amount})"
        )


def process_invoice_items(invoice, payment_method, transaction_id=None):
    for booking in invoice.bookings.all():
        booking.paid = True
        booking.save()
    for membership in invoice.memberships.all():
        membership.paid = True
        membership.save()
    # for gift_voucher in invoice.gift_vouchers.all():
    #     gift_voucher.paid = True
    #     gift_voucher.save()
    #     gift_voucher.activate()

    invoice.paid = True
    invoice.save()
    # SEND EMAILS
    send_processed_payment_emails(invoice)
    # for gift_voucher in invoice.gift_vouchers.all():
    #     gift_voucher.send_voucher_email()
    ActivityLog.objects.create(
        log=f"Invoice {invoice.invoice_id} (user {invoice.username}) paid by {payment_method}"
    )
