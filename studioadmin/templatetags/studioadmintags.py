import pytz

from django import template
from django.utils.safestring import mark_safe

from booking.models import Booking

register = template.Library()


@register.filter
def get_range(value, start=0):
    if  value:
        # start: 0 or 1
        return range(start, value + start)


@register.filter
def bookings_count(event):
    return Booking.objects.select_related('event', 'user').filter(
        event=event, status='OPEN', no_show=False
    ).count()


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
def abbr_username(user):
    if len(user) > 15:
        return mark_safe("{}-</br>{}".format(user[:12], user[12:]))
    return user


@register.filter
def abbr_email(email):
    if len(email) > 25:
        return "{}...".format(email[:22])
    return email


@register.filter
def formatted_uk_date(date):
    """
    return UTC date in uk time
    """
    uk=pytz.timezone('Europe/London')
    return date.astimezone(uk).strftime("%d %b %Y %H:%M")