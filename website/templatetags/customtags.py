from django import template

from timetable.models import TimetableSession

register = template.Library()


@register.filter
def format_day(day_code):
    weekdays = dict(TimetableSession.WEEKDAY_CHOICES)
    return weekdays[day_code]
