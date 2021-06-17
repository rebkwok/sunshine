# -*- coding: utf-8 -*-
from django import forms
from django.utils.safestring import mark_safe
from django.utils import timezone

from suit.widgets import EnclosedInput

from booking.models import Booking, Event


class BookingCreateForm(forms.ModelForm):

    class Meta:
        model = Booking
        fields = ['event', ]

day = 24
week = day * 7

cancel_choices = (
    (day * 0, '0 hours'),
    (day * 1, '24 hours'),
    (day * 2, '2 days'),
    (day * 3, '3 days'),
    (day * 4, '4 days'),
    (day * 5, '5 days'),
    (day * 6, '6 days'),
    (week, '1 week'),
    (week * 2, '2 weeks'),
    (week * 3, '3 weeks'),
    (week * 4, '4 weeks'),
    (week * 5, '5 weeks'),
    (week * 6, '6 weeks'),
)


class EventForm(forms.ModelForm):

    class Meta:
        widgets = {
            # You can also use prepended and appended together
            'cost': EnclosedInput(prepend=u'\u00A3'),
            'cancellation_period': forms.Select(choices=cancel_choices),
            # 'date': SuitSplitDateTimeWidget()
            }
        help_texts = {
            'cancellation_period': mark_safe(
                'Only applicable if "allow booking cancellation" is '
                'ticked.<br/>'
                '0 hours cancellation period means users can cancel and '
                'request refunds at ANY time up to the time of the '
                'workshop.<br/><br/>'
                'Users will still see an option to cancel their booking, '
                'even if cancellation is not allowed, or the cancellation '
                'period is past.  This allows them to notify you of '
                'non-attendance, re-opens their space for booking, and '
                'notifies the waiting list if applicable.'
            ),
            'allow_booking_cancellation': 'If unticked, users will not be '
                                          'eligible for refunds if they '
                                          'cancel at any time after '
                                          'booking.'
        }


def get_names(event_type='regular_session'):

    def callable():
        NAME_CHOICES = list(set(
            Event.objects.select_related('venue')
            .filter(event_type=event_type, date__gte=timezone.now()).order_by('name')
            .values_list('name', 'name')
        ))
        NAME_CHOICES.insert(0, ('all', 'All'))
        return tuple(NAME_CHOICES)

    return callable


def get_venues(event_type='regular_session'):

    def callable():
        VENUE_CHOICES = list(set(
            Event.objects.select_related('venue')
            .filter(event_type=event_type, date__gte=timezone.now()).order_by('venue')
            .values_list('venue__abbreviation', 'venue__abbreviation')
        ))
        VENUE_CHOICES.insert(0, ('all', 'All locations'))
        return tuple(VENUE_CHOICES)

    return callable


class EventsFilter(forms.Form):

    name = forms.ChoiceField(
        choices=(0,0),
        widget=forms.Select(attrs={'class': 'form-control input-xs'})
    )
    venue = forms.ChoiceField(
        choices=(0,0),
        widget=forms.Select(attrs={'class': 'form-control input-xs'})
    )

    def __init__(self, **kwargs):
        event_type = kwargs.pop('event_type', 'regular_session')
        super(EventsFilter, self).__init__()
        initial = kwargs.get('initial')

        self.fields['name'].choices = get_names(event_type=event_type)
        self.fields['venue'].choices = get_venues(event_type)
        if initial:
            self.fields['name'].initial = initial.get('name', 'all')
            self.fields['venue'].initial = initial.get('venue', 'all')
