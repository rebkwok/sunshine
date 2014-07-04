from django import template
from datetime import date, timedelta

register = template.Library()

@register.filter(name='one_week_future')
def one_week_future(value):
    return value + timedelta(days=7)
