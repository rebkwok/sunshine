from os import stat
import pytz

from django import template
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.urls import reverse

from booking.models import Booking

register = template.Library()


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
def formatted_uk_date(date, format):
    """
    return UTC date in uk time
    """
    uk=pytz.timezone('Europe/London')
    return date.astimezone(uk).strftime(format)


@register.filter
def get_register_list_url(event_type, show_all=None):
    url = reverse(f"studioadmin:{event_type}_register_list")
    if show_all:
        url += "?show_all=true"
    return url


@register.inclusion_tag("studioadmin/includes/membership_status.html")
def membership_status(user):
    now = timezone.now()
    current_year = now.year
    current_month = now.month
    paid = user.memberships.filter(paid=True, year__gte=current_year).order_by("year", "month", "purchase_date")
    future_years = paid.filter(year__gt=current_year)
    this_year = paid.filter(year=current_year, month__gte=current_month)
    return {"current_memberships": this_year | future_years}
