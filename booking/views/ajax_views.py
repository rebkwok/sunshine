from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest, JsonResponse
from django.views.decorators.http import require_http_methods
from django.urls import reverse
from django.shortcuts import render, get_object_or_404
from django.template.loader import render_to_string

from activitylog.models import ActivityLog
from booking.views.views_utils import (
    get_unpaid_bookings,
    get_unpaid_memberships,
    get_unpaid_gift_vouchers,
    get_unpaid_gift_vouchers_from_session,
    total_unpaid_item_count,
)
from .booking_helpers import cancel_booking_from_view
from booking.models import Event, Booking, GiftVoucher, Membership, WaitingListUser
from booking.email_helpers import send_email, email_waiting_lists
from booking.utils import calculate_user_cart_total, host_from_request


ITEM_TYPE_MODEL_MAPPING = {
    "membership": Membership,
    "booking": Booking,
    "gift_voucher": GiftVoucher,
}


@login_required
@require_http_methods(["POST"])
def toggle_booking(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    ref = request.GET.get("ref")

    ev_type = "class" if event.event_type != "workshop" else event.event_type

    context = {"event": event, "type": ev_type, "ref": ref}

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
    if existing_booking_status != "OPEN":  # i.e. None (new) or CANCELLED (reopening)
        if request.user.has_outstanding_fees():
            message = "Action forbidden until outstanding cancellation fees have been resolved"
            return HttpResponseBadRequest(message)

        if not event.spaces_left or event.cancelled:
            message = "Sorry, this {} {}".format(
                ev_type,
                "is now full" if not event.spaces_left else "has been cancelled",
            )
            return HttpResponseBadRequest(message)

    if existing_booking_status == "OPEN" and not booking.paid:
        # booking already open and unpaid; user clicked on go-to-basket button
        url = reverse("booking:shopping_basket")
        return JsonResponse({"redirect": True, "url": url})

    if existing_booking_status is None:
        booking = Booking.objects.create(user=request.user, event=event)
    new = existing_booking_status is None

    context["booking"] = booking

    alert_message = {}
    # CANCELLING
    if existing_booking_status == "OPEN":
        # cancel, process refunds etc, email users, email waiting list
        alert_message = cancel_booking_from_view(request, booking)
        action = "cancelled"

    # REOPENING
    elif existing_booking_status == "CANCELLED":
        booking.status = "OPEN"
        booking.no_show = False
        action = "reopened"

    # NEW BOOKING
    elif new:
        booking.status = "OPEN"
        booking.no_show = False
        action = "created"

    if action in ["reopened", "created"]:
        # assign membership if available
        available_user_membership = booking.event.get_available_user_membership(
            booking.user
        )
        if available_user_membership:
            booking.membership = available_user_membership
            booking.paid = True

    booking.save()

    if action != "cancelled" and booking.paid:
        # ONLY SEND EMAILS IF BOOKING IS PAID (i.e. fully booked with membership)
        # Otherwise emails are sent after payment made
        ActivityLog.objects.create(
            log=f'Booking {booking.id} {action} for "{booking.event}" by user {booking.user.username}'
        )
        # send email to user
        ctx = {
            "booking": booking,
            "event": booking.event,
            "date": booking.event.date.strftime("%A %d %B"),
            "time": booking.event.date.strftime("%H:%M"),
            "ev_type": ev_type,
        }

        text_template, html_template = (
            "booking/email/booking_received.txt",
            "booking/email/booking_received.html",
        )
        send_email(
            request,
            "Booking {} for {}".format(action, event.name),
            ctx,
            text_template,
            html_template,
            to_list=[booking.user.email],
        )

        # send email to studio if flagged for the event
        if booking.event.email_studio_when_booked:
            send_email(
                request,
                "{} {} has just booked for {}".format(
                    booking.user.first_name, booking.user.last_name, booking.event
                ),
                ctx,
                "booking/email/to_studio_booking.txt",
                to_list=[settings.DEFAULT_STUDIO_EMAIL],
            )

    # messages for opened/reopened (cancel messages already generated)
    if action in ["created", "reopened"]:
        alert_message["message_type"] = "success"
        if booking.paid:
            alert_message["message"] = "Booked."
        else:
            alert_message["message"] = "Added to basket."
    context["alert_message"] = alert_message

    # remove from waiting list if necessary
    try:
        waiting_list_user = WaitingListUser.objects.get(user=request.user, event=event)
        if action in ["created", "reopened"]:
            waiting_list_user.delete()
            ActivityLog.objects.create(
                log="User {} removed from waiting list for {}".format(
                    request.user.username, event
                )
            )
    except WaitingListUser.DoesNotExist:
        pass

    html = render_to_string(
        "booking/includes/book_button_toggle.html", context, request
    )
    return JsonResponse(
        {
            "html": html,
        }
    )


@login_required
def update_booking_count(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    booked = request.user.bookings.filter(
        event=event, status="OPEN", no_show=False
    ).exists()

    return JsonResponse(
        {
            "booking_count": "{}/{}".format(event.spaces_left, event.max_participants),
            "full": event.spaces_left == 0,
            "booked": booked,
            "cart_item_menu_count": total_unpaid_item_count(request.user),
        }
    )


@login_required
def toggle_waiting_list(request, event_id):
    user = request.user
    event = get_object_or_404(Event, pk=event_id)

    if request.user.has_outstanding_fees():
        message = (
            "Action forbidden until outstanding cancellation fees have been resolved"
        )
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
        {"event": event, "on_waiting_list": on_waiting_list},
    )


@login_required
def booking_details(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    booking = Booking.objects.get(user=request.user, event=event)

    display_status = booking.status
    if booking.status == "OPEN" and booking.no_show:
        display_status = "CANCELLED"

    yes = '<span class="text-success fas fa-check-circle"></span>'
    no = '<span class="text-danger fas fa-times-circle"></span>'
    return JsonResponse(
        {
            "display_status": display_status,
            "status": booking.status,
            "no_show": booking.no_show,
            "display_paid": yes if booking.paid else no,
            "display_membership": (
                f"<a href={reverse('booking:membership_detail', args=(booking.membership.id,))}>{yes}</a>"
                if booking.membership
                else no
            ),
            "cart_item_menu_count": total_unpaid_item_count(request.user),
        }
    )


@require_http_methods(["POST"])
def ajax_cart_item_delete(request):
    item_type = request.POST.get("item_type")
    item_id = request.POST.get("item_id")
    item = get_object_or_404(ITEM_TYPE_MODEL_MAPPING[item_type], pk=item_id)
    if item_type == "booking":
        event = item.event

    unpaid_items = {"booking": [], "membership": [], "gift_voucher": []}
    if request.user.is_authenticated:
        item.delete()
        unpaid_items["membership"] = get_unpaid_memberships(request.user)
        unpaid_items["booking"] = get_unpaid_bookings(request.user)
        unpaid_items["gift_voucher"] = get_unpaid_gift_vouchers(request.user)
        total = calculate_user_cart_total(
            unpaid_items["membership"],
            unpaid_items["booking"],
            unpaid_items["gift_voucher"],
        )
        unpaid_item_count = total_unpaid_item_count(request.user)
    else:
        assert item_type == "gift_voucher"
        gift_vouchers_on_session = request.session.get("purchases", {}).get(
            "gift_vouchers", []
        )
        if int(item_id) in gift_vouchers_on_session:
            gift_vouchers_on_session.remove(int(item_id))
            request.session["purchases"]["gift_vouchers"] = gift_vouchers_on_session
            item.delete()
        unpaid_items["gift_voucher"] = get_unpaid_gift_vouchers_from_session(request)
        unpaid_item_count = unpaid_items["gift_voucher"].count()
        total = calculate_user_cart_total(
            unpaid_gift_vouchers=unpaid_items["gift_voucher"]
        )
    if item_type == "booking":
        # send waiting list emails if necessary
        email_waiting_lists([event.id], host=host_from_request(request))

    if not unpaid_items[item_type]:
        return JsonResponse(
            {
                "redirect": True,
                "url": reverse("booking:shopping_basket"),
            }
        )

    return JsonResponse(
        {
            "cart_total": total,
            "cart_item_menu_count": unpaid_item_count,
        }
    )
