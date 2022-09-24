from django.conf import settings
from django.core.mail import send_mail
from django.contrib.sites.models import Site
from django.template.loader import get_template 

import stripe

from activitylog.models import ActivityLog
from booking.email_helpers import email_waiting_lists, send_email
from booking.utils import host_from_request
from stripe_payments.models import Seller, StripePaymentIntent, StripeRefund


def cancel_booking_from_view(request, booking):
    # 1) check if the booking can be cancelled
    # 2) check if it can be cancelled b/c it's membership booked within 15 mins
    # 3) Was it paid? - Yes
    #    a) Do we need to refund it?
    #    b) Do we need to put it back on a membership?
    # 4) Was it paid? - No
    # 5) Set it to cancelled/no-show/unpaid
    # 6) Email user (if previoulsy paid)
    # 7) Email waiting list users if required

    event = booking.event
    delete_from_shopping_basket = request.GET.get('ref') == 'basket'

    # Booking can be fully cancelled if the event allows cancellation AND
    # the cancellation period is not past
    # If not, we let people cancel but leave the booking status OPEN and
    # set to no-show
    can_cancel_and_refund = booking.event.allow_booking_cancellation and event.can_cancel()

    # if the booking was made with a membership, allow 5 mins to cancel in case user
    # clicked the wrong button by mistake and autobooked with a membership
    # Check here so we can adjust the email message
    membership_booking_within_5_mins = booking.booked_with_membership_within_allowed_time()
    was_booked_with_membership = booking.membership is not None
    was_paid = booking.paid

    refunded = False
    if can_cancel_and_refund:
        if booking.membership:
            # booked with membership, remove from membership and set paid to False
            booking.membership = None
            booking.paid = False
        else:
            # Paid directly; find invoice/payment intent (if it exists), process refund
            if booking.invoice:
                refunded = process_refund()
                
            # mark unpaid whether refunded or not
            # if there was no associated invoice, it was manually booked by an admin, or it wasn't paid yet
            booking.paid = False
        booking.status = 'CANCELLED'
        booking.save()
    
    else:
        # The cancellation is being requested after the cancellation period, or for an event
        # that doesn't allow cancellation.  It can still be cancelled if:
        # - it wasn't paid OR
        # - it was just made with a membership: allow 5 mins to cancel in case user
        #   clicked the wrong button by mistake and autobooked with a membership
        can_cancel = membership_booking_within_5_mins or not booking.paid
        if can_cancel:
            booking.membership = None
            booking.paid = False
            booking.status = 'CANCELLED'
            booking.save()
        else:  # set to no-show
            booking.no_show = True
            booking.save()

    # MESSAGES
    alert_message = {"message_type": "error"}
    # no messages if we're deleting from shopping basket
    if not delete_from_shopping_basket:
        alert_message["message"] = "Cancelled."
        if booking.status == "CANCELLED":
            if refunded: 
                alert_message["message"] += " Refund processing."
            ActivityLog.objects.create(
                log='Booking id {} for event {}, user {}, was cancelled by user '
                    '{}'.format(
                        booking.id, booking.event, booking.user.username,
                        request.user.username
                    )
                )                
        elif booking.no_show:
            if not booking.event.allow_booking_cancellation:
                alert_message["message"] += ' Please note that this booking is not eligible for '\
                    'refunds or transfer credit.'
                ActivityLog.objects.create(
                    log='Booking id {} for NON-CANCELLABLE event {}, user {}, '
                        'was cancelled and set to no-show'.format(
                            booking.id, booking.event, booking.user.username,
                            request.user.username
                        )
                )
            else:
                alert_message["message"] += (
                    ' Please note that this booking is not eligible for '
                    'refunds as the allowed cancellation period has passed.'
                )
                ActivityLog.objects.create(
                    log='Booking id {} for event {}, user {}, was cancelled '
                        'after the cancellation period and set to '
                        'no-show'.format(
                            booking.id, booking.event, booking.user.username,
                            request.user.username
                        )
                )
    
    # EMAIL USER
    # Only send emails if booking was previously paid; we don't want to send emails
    # if just removing from basked
    if was_paid:
        host = host_from_request(request)
        ctx = {
            'host': host,
            'booking': booking,
            'was_booked_with_membership': was_booked_with_membership,
            'membership_booked_within_allowed_time': membership_booking_within_5_mins,
            'refunded': refunded,
            'event': booking.event,
        }
        send_mail('{} Booking for {} cancelled'.format(
            settings.ACCOUNT_EMAIL_SUBJECT_PREFIX, booking.event),
            get_template('booking/email/booking_cancelled.txt').render(ctx),
            settings.DEFAULT_FROM_EMAIL,
            [booking.user.email],
            html_message=get_template(
                'booking/email/booking_cancelled.html').render(ctx),
            fail_silently=False)
        
        # EMAIL STUDIO
        if settings.SEND_ALL_STUDIO_EMAILS:
            send_mail('{} Booking for {} cancelled'.format(
                settings.ACCOUNT_EMAIL_SUBJECT_PREFIX, booking.event),
                get_template('booking/email/to_studio_booking_cancelled.txt').render(ctx),
                settings.DEFAULT_FROM_EMAIL,
                [settings.DEFAULT_STUDIO_EMAIL],
                fail_silently=False)

    # WAITING LIST
    # if applicable, email users on waiting list
    email_waiting_lists([event.id], host=host)

    return alert_message


def process_refund(request, booking):
    # process refund
    refunded = False
    try:
        payment_intent = StripePaymentIntent.objects.get(
            payment_intent_id=booking.invoice.stripe_payment_intent_id
        )
    except StripePaymentIntent.DoesNotExist:
        # send warning email to tech support
        _send_invalid_request_email(
            request, booking, "Payment intent not found"
        )
    else:
        stripe.api_key = settings.STRIPE_SECRET_KEY
        seller = Seller.objects.filter(site=Site.objects.get_current(request)).first()
        
        # get the amount to refund from the metadata (in) pence)
        amount = payment_intent.metadata.get(f"booking_{booking.id}_cost_in_p")
        if amount is None:
            # send warning email to tech support
            _send_invalid_request_email(
                request, booking, "Amount could not be parsed from PI metadata"
            )
        else:
            try:
                refund = stripe.Refund.create(
                    amount=int(amount),
                    metadata={"booking_id": booking.id, "cancelled_by": request.user.email},
                    payment_intent=payment_intent.payment_intent_id,
                    reason="requested_by_customer",
                    stripe_account=seller.stripe_user_id,
                )
                StripeRefund.create_from_refund_obj(refund, payment_intent, booking.id)
                refunded = True
                ActivityLog.objects.create(
                    log=f"Refund for booking {booking.id} (user {booking.user.username}) processed"
                )
            except stripe.error.InvalidRequestError as error:
                # send warning email to tech support
                _send_invalid_request_email(request, booking, str(error))
    return refunded


def _send_invalid_request_email(request, booking, reason):
    # send warning email to tech support
    send_email(
        request, 
        subject="Refund failed: amount could not be calculated",
        template_txt="booking/email/refund_failed.txt",
        ctx={
            "payment_intent": booking.invoice.stripe_payment_intent_id,
            "invoice": booking.invoice.invoice_id,
            "booking_id": booking.id,
            "reason": reason
        },
        to_list=[settings.SUPPORT_EMAIL],
    )