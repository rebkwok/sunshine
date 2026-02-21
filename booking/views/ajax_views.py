import json

from urllib.parse import parse_qs, urlsplit, urlunsplit, urlencode

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest, JsonResponse, HttpResponse
from django.template.response import TemplateResponse
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
def toggle_waiting_list(request, event_id):
    user = request.user
    event = get_object_or_404(Event, pk=event_id)
    ev_type = "class" if event.event_type != "workshop" else event.event_type
    tab = request.POST.get("tab")
    ref = request.POST.get("ref", "event")
    booking_id = request.POST.get("booking_id")

    if booking_id:
        booking = request.user.bookings.get(id=int(booking_id))
    else:
        booking = None

    if request.user.has_outstanding_fees():
        message = (
            "Action forbidden until outstanding cancellation fees have been resolved"
        )
        return HttpResponseBadRequest(message)

    # toggle current status
    try:
        waitinglistuser = WaitingListUser.objects.get(user=user, event=event)
        waitinglistuser.delete()
    except WaitingListUser.DoesNotExist:
        WaitingListUser.objects.create(user=user, event=event)

    headers = _get_redirect_headers(request, tab)
    context = {"event": event, "type": ev_type, "booking": booking}
    return TemplateResponse(
        request, f"booking/includes/{ref}_row.html", context, headers=headers
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


@login_required
@require_http_methods(["POST"])
def toggle_booking(request, event_id):
    event = get_object_or_404(Event, pk=event_id)

    ev_type = "class" if event.event_type != "workshop" else event.event_type

    context = {"event": event, "type": ev_type}

    existing_booking_status = None
    booking_id = request.POST.get("booking_id")
    tab = request.POST.get("tab")
    ref = request.POST.get("ref", "event")
    if booking_id:
        booking = request.user.bookings.get(id=int(booking_id))
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
        return HttpResponse("", headers={"Hx-Redirect": url})

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
        context["is_booked"] = True
        alert_message["level"] = "success"
        if booking.paid:
            alert_message["message"] = "Booked."
        else:
            alert_message["message"] = "Added to basket."

    context["cart_item_count"] = total_unpaid_item_count(request.user)

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

    headers = _get_redirect_headers(request, tab)

    if alert_message:
        headers["Hx-Trigger"] = json.dumps(
            {
                "showAlert": {
                    "level": alert_message["level"],
                    "message": alert_message["message"],
                    "title": str(event),
                }
            }
        )

    return TemplateResponse(
        request, f"booking/includes/{ref}_row.html", context, headers=headers
    )


def _get_redirect_headers(request, tab):
    headers = {}
    tab = int(tab) if tab else 0
    # redirect if tab is not 0 or user now has fees outstanding
    if (tab != 0) or request.user.has_outstanding_fees():
        spliturl = urlsplit(request.META["HTTP_REFERER"])
        querystring_dict = parse_qs(spliturl.query)
        if tab:
            querystring_dict["tab"] = int(tab)
        redirect_url = urlunsplit(
            (
                spliturl.scheme,
                spliturl.netloc,
                spliturl.path,
                urlencode(querystring_dict),
                spliturl.fragment,
            )
        )
        headers = {"Hx-Redirect": redirect_url}
    return headers
