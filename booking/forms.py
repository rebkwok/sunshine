# -*- coding: utf-8 -*-
from django import forms
from django.contrib.auth.models import User
from django.utils.safestring import mark_safe

from suit.widgets import EnclosedInput, SuitSplitDateTimeWidget

from booking.models import Booking


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
            'date': SuitSplitDateTimeWidget()
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


class UserModelChoiceField(forms.ModelChoiceField):

    def label_from_instance(self, obj):
        return "{} {} ({})".format(obj.first_name, obj.last_name, obj.username)

    def to_python(self, value):
        if value:
            return User.objects.get(id=value)


class BookingInlineFormset(forms.BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        super(BookingInlineFormset, self).__init__(*args, **kwargs)

        for form in self.forms:
            booked_ids = [bk.user.id for bk in self.instance.bookings.all()]
            form.fields['user'] = UserModelChoiceField(
                queryset=User.objects.exclude(id__in=booked_ids)
            )
            if form.instance.id:
                form.fields['user'].queryset = User.objects.filter(
                    id=form.instance.user.id
                )
                if form.instance.paid:
                    form.fields['DELETE'].widget = forms.HiddenInput()
