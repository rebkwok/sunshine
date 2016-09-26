from datetime import date, timedelta
from django.core import exceptions, validators
from django.forms import widgets, Field
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils.html import mark_safe


HOURS_CONVERSION = {
        'weeks': 7 * 24,
        'days': 24,
    }


class DurationSelectorWidget(widgets.MultiWidget):

    def __init__(self, attrs=None):

        weeks = [(week, week) for week in range(0, 52)]
        days = [(day, day) for day in range(0, 7)]
        hours = [(hr, hr) for hr in range(0, 24)]
        _widgets = (
            widgets.Select(attrs=attrs, choices=weeks),
            widgets.Select(attrs=attrs, choices=days),
            widgets.Select(attrs=attrs, choices=hours),
        )

        super(DurationSelectorWidget, self).__init__(_widgets, attrs)

    def decompress(self, value):
        if value:
            # convert from hours
            weeks = value // HOURS_CONVERSION['weeks']
            weeks_remainder = value % HOURS_CONVERSION['weeks']
            days = weeks_remainder // HOURS_CONVERSION['days']
            hours = weeks_remainder % HOURS_CONVERSION['days']
            return [weeks, days, hours]
        return [None, None, None]

    def format_output(self, rendered_widgets):
        return (
            "<div>Weeks:</div> {}"
            "<div>Days:</div>{}"
            "<div>Hours:</div>{}"
            .format(
                rendered_widgets[0], rendered_widgets[1], rendered_widgets[2]
            )
        )

    def value_from_datadict(self, data, files, name):
        weeks_days_hours = [
            widget.value_from_datadict(data, files, name + '_%s' % i)
            for i, widget in enumerate(self.widgets)]

        hours_duration = int(weeks_days_hours[0]) * HOURS_CONVERSION['weeks'] \
                  + int(weeks_days_hours[1]) * HOURS_CONVERSION['days'] \
                  + int(weeks_days_hours[2])

        return hours_duration
