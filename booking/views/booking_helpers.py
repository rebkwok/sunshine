from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.template.loader import get_template 
from activitylog.models import ActivityLog

from ..models import WaitingListUser
from ..email_helpers import send_waiting_list_email



def cancel_booking_from_view(request, booking):
    # 1) check if the booking can be cancelled
    # 2) check if it can be cancelled b/c it's membership booked within 15 mins
    # 3) Was it paid? - Yes
    #    a) Do we need to refund it?
    #    b) Do we need to put it back on a membership?
    # 4) Was it paid? - No
    # 5) Set it to cancelled/no-show/unpaid
    # 6) Email user
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

    refunded = False
    if can_cancel_and_refund:
        if booking.membership:
            # booked with membership, remove from membership and set paid to False
            booking.membership = None
            booking.paid = False
        else:
            # Paid directly; find invoice/payment intent (if it exists), process refund
            # if invoice etc:
            #     process refund
            #     booking.paid = False
            #     refunded = True
            # else:
            # no associated invoice, it was manually booked by an admin, or it wasn't paid yet
            #     booking.paid = False
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
        base_msg = f'Booking cancelled for {booking.event}.'
        base_alert_msg = "Cancelled"
        if booking.status == "CANCELLED":
            alert_message["message"] = "Cancelled."
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
    ctx = {
        'host': f"http://{request.META.get('HTTP_HOST')}",
        'booking': booking,
        'was_booked_with_membership': was_booked_with_membership,
        'membership_booked_within_allowed_time': membership_booking_within_5_mins,
        'refunded': refunded,
        'event': booking.event,
        'date': booking.event.date.strftime('%A %d %B'),
        'time': booking.event.date.strftime('%I:%M %p'),
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
    email_waiting_list(request, event)

    return alert_message


def email_waiting_list(request, event):
    # WAITING LIST
    # if applicable, email users on waiting list
    waiting_list_users = WaitingListUser.objects.filter(
        event=event
    )
    if waiting_list_users:
        send_waiting_list_email(
            event,
            [wluser.user for wluser in waiting_list_users],
            host='http://{}'.format(request.META.get('HTTP_HOST'))
        )
        ActivityLog.objects.create(
            log='Waiting list email sent to user(s) {} for '
            'event {}'.format(
                ', '.join(
                    [wluser.user.username for \
                    wluser in waiting_list_users]
                ),
                event
            )
        )