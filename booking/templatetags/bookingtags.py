import os
import pytz

from datetime import datetime

from django.conf import settings
from django.contrib.auth.models import Group
from django import template
from django.utils import timezone
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
def get_range(value):
    return range(value)


@register.filter
def get_index_open(event, extraline_index):
    open_bookings = [
        booking for booking in event.bookings.all() if booking.status == 'OPEN'
        ]
    return len(open_bookings) + 1 + extraline_index


@register.filter
def bookings_count(event):
    return Booking.objects.select_related('event', 'user').filter(
        event=event, status='OPEN', no_show=False
    ).count()


@register.filter
def format_field_name(field):
    return field.replace('_', ' ').title()


@register.filter
def formatted_uk_date(date):
    """
    return UTC date in uk time
    """
    uk=pytz.timezone('Europe/London')
    return date.astimezone(uk).strftime("%d %b %Y %H:%M")

@register.filter
def abbr_username(user):
    if len(user) > 15:
        return mark_safe("{}-</br>{}".format(user[:12], user[12:]))
    return user

@register.filter
def abbr_name(name):
    if len(name) > 8 and '-' in name:
        split_name = name.split('-')
        return mark_safe(
            "{}-</br>{}".format(split_name[0], '-'.join(split_name[1:]))
        )
    if len(name) > 12:
        return mark_safe("{}-</br>{}".format(name[:8], name[8:]))
    return name

@register.filter
def abbr_email(email):
    if len(email) > 25:
        return "{}...".format(email[:22])
    return email

@register.filter
def subscribed(user):
    group, _ = Group.objects.get_or_create(name='subscribed')
    return group in user.groups.all()


@register.filter
def format_block_type_identifier(value):
    if value:
        if value.startswith('transferred'):
            return '(transfer)'
        return '({})'.format(value)
    return ''


@register.filter
def format_paid_status(booking):
    if booking.paid:
        return mark_safe('<span class="confirmed fa fa-check"></span>')
    else:
        return mark_safe('<span class="not-confirmed fa fa-close"></span>')


@register.assignment_tag
def check_debug():
    return settings.DEBUG
