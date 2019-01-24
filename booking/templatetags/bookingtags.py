# -*- coding: utf-8 -*-

from django.conf import settings
from django import template
from django.utils.safestring import mark_safe

from booking.models import Booking


register = template.Library()

HOURS_CONVERSION = {
    'weeks': 7 * 24,
    'days': 24,
}


@register.filter
def format_cancellation(value):
    """
    Convert cancellation period in hours into formatted text
    """
    weeks = value // HOURS_CONVERSION['weeks']
    weeks_remainder = value % HOURS_CONVERSION['weeks']
    days = weeks_remainder // HOURS_CONVERSION['days']
    hours = weeks_remainder % HOURS_CONVERSION['days']

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
            plural_format(hours)
        )


def plural_format(value):
    if value > 1 or value == 0:
        return "s"
    else:
        return ""


@register.filter
def format_paid_status(booking):
    if booking.paid:
        return mark_safe('<span class="confirmed fas fa-check"></span>')
    else:
        return mark_safe('<span class="not-confirmed fas fa-times"></span>')


@register.simple_tag
def get_booking(event, user):
    if user.is_authenticated:
        return Booking.objects.filter(event=event, user=user).first()
    return None


@register.filter
def get_range(value, start=0):
    # start: 0 or 1
    return range(start, value + start)


@register.filter
def lookup(dictionary, key):
    if dictionary:
        return dictionary.get(key)

@register.filter
def renderpaypalform(paypalforms_dict, key):
    return paypalforms_dict[key].render()
