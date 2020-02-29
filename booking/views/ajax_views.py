from datetime import timedelta

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest, HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.shortcuts import render, get_object_or_404

from activitylog.models import ActivityLog
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
    if Booking.objects.filter(user=request.user, event=event).exists():
        booking = Booking.objects.get(user=request.user, event=event)
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
    event_was_full = False
    if existing_booking_status == "OPEN":
        event_was_full = event.spaces_left == 0
        # allow 15 mins to properly cancel in case user clicked the wrong button by mistake
        # Otherwise, booking can be fully cancelled if the event allows cancellation AND
        # the cancellation period is not past
        # If not, we let people cancel but leave the booking status OPEN and
        # set to no-show
        booked_within_allowed_time = _booked_within_allowed_time(booking)
        can_cancel = booked_within_allowed_time or (event.allow_booking_cancellation and event.can_cancel())
        if can_cancel:
            booking.status = 'CANCELLED'
        else:
            booking.no_show = True
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

    booking.save()

    ActivityLog.objects.create(
        log='Booking {} {} for "{}" by user {}'.format(
            booking.id, action, booking.event, booking.user.username)
    )

    host = 'http://{}'.format(request.META.get('HTTP_HOST'))
    # send email to user

    # send email to user
    ctx = {
          'booking': booking,
          'event': booking.event,
          'date': booking.event.date.strftime('%A %d %B'),
          'time': booking.event.date.strftime('%H:%M'),
          'ev_type': 'workshop'
    }

    if action == 'cancelled':
        text_template, html_template = (
            'booking/email/booking_cancelled.txt', 'booking/email/booking_cancelled.html'
        )
    else:
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

    # send waiting list email if event was full before this cancellation
    if event_was_full:
        waiting_list_users = WaitingListUser.objects.filter(event=event)
        if waiting_list_users:
            send_waiting_list_email(
                event,
                [wluser.user for wluser in waiting_list_users],
                host='http://{}'.format(request.META.get('HTTP_HOST'))
            )

    alert_message = {}

    if action in ['created', 'reopened']:
        alert_message['message_type'] = 'success'
        alert_message['message'] = "Booked."
    else:
        alert_message['message_type'] = 'error'
        alert_message['message'] = "Cancelled."

    try:
        waiting_list_user = WaitingListUser.objects.get(
            user=booking.user, event=booking.event
        )
        if action in ['created', 'reopened']:
            waiting_list_user.delete()
            ActivityLog.objects.create(
                log='User {} removed from waiting list '
                'for {}'.format(
                    booking.user.username, booking.event
                )
            )
    except WaitingListUser.DoesNotExist:
        pass

    context["alert_message"] = alert_message

    return render(
        request,
        "booking/includes/book_button_toggle.html",
        context
    )


def _booked_within_allowed_time(booking):
    allowed_datetime = timezone.now() - timedelta(minutes=15)
    return (booking.date_rebooked and booking.date_rebooked > allowed_datetime) \
        or (booking.date_booked > allowed_datetime)


@login_required
def update_booking_count(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    booked = Booking.objects.filter(
        user=request.user, event=event, status='OPEN', no_show=False
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

