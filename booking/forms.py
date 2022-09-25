# -*- coding: utf-8 -*-
from django import forms
from django.utils.safestring import mark_safe
from django.utils import timezone

from suit.widgets import EnclosedInput
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit

from booking.models import Booking, Event, GiftVoucher, GiftVoucherType, ItemVoucher, MembershipType


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



class ItemVoucherForm(forms.ModelForm):

    class Meta:
        model = ItemVoucher
        fields = "__all__"
        labels = {
            "start_date": "Start date and time",
            "expiry_date": "Expiry date and time (optional)",
            "discount": "Discount %"
        }
        help_texts = {
            "code": "Voucher codes are case sensitive; must not contain spaces",
            "max_vouchers": "Maximum uses across all users; leave blank for no maximum",
            "max_per_user": "Maximum uses per users; leave blank for no maximum",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['event_types'] = forms.MultipleChoiceField(
            choices=Event.EVENT_TYPES, required=False,
            widget=forms.CheckboxSelectMultiple
        )
        self.fields['membership_types'] = forms.ModelMultipleChoiceField(
            queryset=MembershipType.objects.all(), required=False,
            widget=forms.CheckboxSelectMultiple
        )

    def clean_code(self):
        code = self.cleaned_data['code']
        if len(code.split()) > 1:
            self.add_error("code", "Code cannot contain spaces")
        return code

    def clean(self):
        membership_types = self.cleaned_data.get('membership_types')
        event_types = self.cleaned_data.get('event_types')
        if not (membership_types or event_types):
            self.add_error(None, "Specify at least one membership type or event type that this voucher is valid for")



class GiftVoucherForm(forms.ModelForm):

    user_email = forms.EmailField(
        label="Email address:",
        widget=forms.TextInput(attrs={"class": "form-control"})
    )
    user_email1 = forms.EmailField(
        label="Confirm email address:",
        widget=forms.TextInput(attrs={"class": "form-control"})
    )
    recipient_name = forms.CharField(
        label="Recipient name to display on voucher (optional):",
        widget=forms.TextInput(attrs={"class": "form-control"}),
        required=False
    )
    message = forms.CharField(
        label="Message to display on voucher (optional):",
        widget=forms.Textarea(attrs={"class": "form-control", 'rows': 4}),
        required=False,
        max_length=500,
        help_text="Max 500 characters"
    )

    class Meta:
        model = GiftVoucher
        fields = ("gift_voucher_type",)

    def __init__(self, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(**kwargs)

        self.fields["gift_voucher_type"].queryset = GiftVoucherType.objects.filter(active=True)
        self.fields["gift_voucher_type"].label = "Select gift voucher type:"

        if self.instance.id:
            voucher = self.instance.voucher
            self.fields["user_email"].initial = voucher.purchaser_email
            self.fields["user_email1"].initial = voucher.purchaser_email
            if voucher.activated:
                self.fields["gift_voucher_type"].disabled = True
                self.fields["user_email"].disabled = True
                self.fields["user_email1"].disabled = True
            self.fields["recipient_name"].initial = voucher.name
            self.fields["message"].initial = voucher.message
        elif user:
            self.fields["user_email"].initial = user.email
            self.fields["user_email1"].initial = user.email
            self.fields["user_email"].disabled = True
            self.fields["user_email1"].disabled = True

        self.helper = FormHelper()
        if self.instance.id:
            submit_button = Submit('submit', 'Update')
        else:
            submit_button = Submit('submit', 'Add to cart') if user is not None else Submit('submit', 'Checkout as guest')

        self.helper.layout = Layout(
            "gift_voucher_type",
            "user_email",
            "user_email1",
            "recipient_name",
            "message",
            submit_button
        )

    def clean_user_email(self):
        return self.cleaned_data.get('user_email').strip()

    def clean_user_email1(self):
        return self.cleaned_data.get('user_email1').strip()

    def clean(self):
        user_email = self.cleaned_data["user_email"]
        user_email1 = self.cleaned_data["user_email1"]
        if user_email != user_email1:
            self.add_error("user_email1", "Email addresses do not match")

    def save(self, commit=True):
        gift_voucher = super().save(commit=commit)
        if commit:
            gift_voucher.voucher.name = self.cleaned_data["recipient_name"]
            gift_voucher.voucher.message = self.cleaned_data["message"]
            gift_voucher.voucher.purchaser_email = self.cleaned_data["user_email"]
            gift_voucher.voucher.save()
        return gift_voucher
