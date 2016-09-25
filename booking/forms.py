# -*- coding: utf-8 -*-
from django import forms

from booking.models import Booking


class BookingCreateForm(forms.ModelForm):

    class Meta:
        model = Booking
        fields = ['event', ]

