# -*- coding: utf-8 -*-

from django import template

from booking.models import Booking, WaitingListUser


register = template.Library()

HOURS_CONVERSION = {
    "weeks": 7 * 24,
    "days": 24,
}


@register.filter
def format_cancellation(value):
    """
    Convert cancellation period in hours into formatted text
    """
    weeks = value // HOURS_CONVERSION["weeks"]
    weeks_remainder = value % HOURS_CONVERSION["weeks"]
    days = weeks_remainder // HOURS_CONVERSION["days"]
    hours = weeks_remainder % HOURS_CONVERSION["days"]

    if value <= 24:
        return "{} hour{}".format(value, plural_format(value))
    elif weeks == 0 and hours == 0:
        return "{} day{}".format(days, plural_format(days))
    elif days == 0 and hours == 0:
        return "{} week{}".format(weeks, plural_format(weeks))
    else:
        return "{} week{}, {} day{} and {} hour{}".format(
            weeks,
            plural_format(weeks),
            days,
            plural_format(days),
            hours,
            plural_format(hours),
        )


def plural_format(value):
    if value > 1 or value == 0:
        return "s"
    else:
        return ""


@register.simple_tag
def get_booking(event, user):
    if user.is_authenticated:
        return Booking.objects.filter(event=event, user=user).first()
    return None


@register.filter
def get_range(value, start=0):
    # start: 0 or 1
    return range(start, value + start)


@register.simple_tag
def book_button_data(event, user, booking, ref):
    if user.is_anonymous:
        has_available_membership = False
        on_waiting_list = False
    else:
        has_available_membership = bool(event.get_available_user_membership(user))
        on_waiting_list = WaitingListUser.objects.filter(
            user=user, event=event
        ).exists()

    if booking:
        is_booked = booking.status == "OPEN" and not booking.no_show
        is_booked_and_unpaid = is_booked and not booking.paid
        is_cancelled = booking.status == "CANCELLED" or booking.no_show
        can_cancel = is_booked and booking.paid
    else:
        is_booked = False
        is_booked_and_unpaid = False
        is_cancelled = False
        can_cancel = False
    return {
        "show_book_button": event.bookable or is_booked,
        "ref": ref,
        "event": event,
        "members_only_not_allowed": (
            event.members_only and not is_booked and not has_available_membership
        ),
        "is_booked": is_booked,
        # button action
        "can_cancel": can_cancel,
        "can_rebook": is_cancelled and has_available_membership,
        "can_book": not is_booked and not is_cancelled and has_available_membership,
        "can_go_to_basket": is_booked_and_unpaid and not has_available_membership,
        "can_add_to_basket": (
            event.bookable
            and not user.is_anonymous
            and not is_booked
            and not has_available_membership
        ),
        "show_cancellation_warning": (
            can_cancel and not event.can_cancel() and event.cancellation_fee > 0
        ),
        "on_waiting_list": on_waiting_list,
    }
