from datetime import timedelta

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest, HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.shortcuts import render, get_object_or_404

from activitylog.models import ActivityLog
from .booking_helpers import cancel_booking_from_view
from booking.models import Event, Booking, WaitingListUser
from booking.email_helpers import send_email, send_waiting_list_email


@login_required
@require_http_methods(['POST'])
def toggle_booking(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    ref = request.GET.get('ref')

    if event.event_type == 'regular_session':
        ev_type = 'class'
    else:
        ev_type = 'workshop'

    context = {
        "event": event, "type": ev_type,
        "ref": ref
    }

    existing_booking_status = None
    # check booking status and make new booking
    if request.user.bookings.filter(event=event).exists():
        booking = request.user.bookings.get(event=event)
        if booking.status == "CANCELLED" or booking.no_show:
            existing_booking_status = "CANCELLED"
        else:
            existing_booking_status = "OPEN"

    # if making a new/reopening booking, make sure the event isn't full or cancelled
    # and abort if user has outstanding fees
    if existing_booking_status != 'OPEN':  # i.e. None (new) or CANCELLED (reopening)
        if request.user.has_outstanding_fees():
            message = f"Action forbidden until outstanding cancellation fees have been resolved"
            return HttpResponseBadRequest(message)

        if not event.spaces_left or event.cancelled:
            message = "Sorry, this {} {}".format(
                ev_type, 'is now full' if not event.spaces_left else "has been cancelled"
            )
            return HttpResponseBadRequest(message)

    if existing_booking_status is None:
        booking = Booking.objects.create(user=request.user, event=event)
    new = existing_booking_status is None

    context['booking'] = booking

    # CANCELLING
    refunded = False
    if existing_booking_status == "OPEN":
        # cancel, process refunds etc, email users, email waiting list
        refunded = cancel_booking_from_view(request, booking)
        action = 'cancelled'

    # REOPENING
    elif existing_booking_status == "CANCELLED":
        booking.status = 'OPEN'
        booking.no_show = False
        action = 'reopened'

    # NEW BOOKING
    elif new:
        booking.status = 'OPEN'
        booking.no_show = False
        action = 'created'

    if action in ["reopened", "created"]:
        # assign membership if available
        available_user_membership = booking.event.get_available_user_membership(booking.user)
        if available_user_membership:
            booking.user_membership = available_user_membership
            booking.paid = True

    booking.save()

    if action != "cancelled":
        ActivityLog.objects.create(
            log=f'Booking {booking.id} {action} for "{booking.event}" by user {booking.user.username}'
        )
        # send email to user
        ctx = {
            'booking': booking,
            'event': booking.event,
            'date': booking.event.date.strftime('%A %d %B'),
            'time': booking.event.date.strftime('%H:%M'),
            'ev_type': 'workshop'
        }

        text_template, html_template = (
            'booking/email/booking_received.txt', 'booking/email/booking_received.html'
        )
        send_email(
            request,
            'Booking {} for {}'.format(action, event.name),
            ctx,
            text_template,
            html_template,
            to_list=[booking.user.email],
        )

        # send email to studio if flagged for the event
        if booking.event.email_studio_when_booked:
            send_email(
                request,
                '{} {} has just {} for {}'.format(
                    booking.user.first_name, booking.user.last_name,
                    'cancelled a booking' if action == 'cancelled' else 'booked',
                    booking.event
                ),
                ctx,
                'booking/email/to_studio_booking_cancelled.txt' if action == 'cancelled'
                else 'booking/email/to_studio_booking.txt',
                to_list=[settings.DEFAULT_STUDIO_EMAIL]
            )

    alert_message = {}

    if action in ['created', 'reopened']:
        alert_message['message_type'] = 'success'
        if booking.paid:
            alert_message['message'] = "Booked."
        else:
            alert_message['message'] = "Added to basket."
    else:
        alert_message['message_type'] = 'error'
        msg = "Cancelled."
        if refunded:
            msg += " Refund processing."
        alert_message['message'] = msg

    context["alert_message"] = alert_message

    # remove from waiting list if necessary
    try:
        waiting_list_user = WaitingListUser.objects.get(
            user=request.user, event=event
        )
        if action in ['created', 'reopened']:
            waiting_list_user.delete()
            ActivityLog.objects.create(
                log='User {} removed from waiting list '
                'for {}'.format(
                    request.user.username, event
                )
            )
    except WaitingListUser.DoesNotExist:
        pass
    
    return render(
        request,
        "booking/includes/book_button_toggle.html",
        context
    )


@login_required
def update_booking_count(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    booked = request.user.bookings.filter(
        event=event, status='OPEN', no_show=False
    ).exists()

    return JsonResponse(
        {
            'booking_count': "{}/{}".format(event.spaces_left, event.max_participants),
            'full': event.spaces_left == 0,
            'booked': booked
        }
    )


@login_required
def toggle_waiting_list(request, event_id):
    user = request.user
    event = get_object_or_404(Event, pk=event_id)

    if request.user.has_outstanding_fees():
        message = f"Action forbidden until outstanding cancellation fees have been resolved"
        return HttpResponseBadRequest(message)

    # toggle current status
    try:
        waitinglistuser = WaitingListUser.objects.get(user=user, event=event)
        waitinglistuser.delete()
        on_waiting_list = False
    except WaitingListUser.DoesNotExist:
        WaitingListUser.objects.create(user=user, event=event)
        on_waiting_list = True

    return render(
        request,
        "booking/includes/waiting_list_toggle.html",
        {'event': event, 'on_waiting_list': on_waiting_list}
    )


@login_required
def booking_details(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    booking = Booking.objects.get(user=request.user, event=event)

    display_status = booking.status
    if booking.status == 'OPEN' and booking.no_show:
        display_status = 'CANCELLED'
    return JsonResponse(
        {
            'display_status': display_status,
            'status': booking.status,
            'no_show': booking.no_show,
            'display_paid': '<span class="confirmed fas fa-check"></span>' if booking.paid
            else '<span class="not-confirmed fas fa-times"></span>'
        }
    )

