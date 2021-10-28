import datetime
import pytz
from django import forms
from django.utils import timezone
from django.utils.html import mark_safe


DAYS = {
    '01MO': 0,
    '02TU': 1,
    '03WE': 2,
    '04TH': 3,
    '05FR': 4,
    '06SA': 5,
    '07SU': 6
    }


def get_dates(session):
    day = DAYS[session.session_day]
    local_now = timezone.now().astimezone(pytz.timezone('Europe/London'))

    days_ahead = day - local_now.weekday()

    # already happened this week (either previous day or earlier today)
    if days_ahead < 0 or \
            (days_ahead == 0 and local_now.time() > session.start_time):
        days_ahead += 7
    next_date = timezone.now() + datetime.timedelta(days_ahead)

    next_dates = [next_date] + \
                 [next_date + datetime.timedelta(i * 7) for i in range(1, 4)]

    date_choices = sorted(
        [
            (i+1, date.strftime('%a %d %b %y'))
            for i, date in enumerate(next_dates)
            ]
    )
    date_choices.insert(4, (4, 'Regular weekly booking'))
    date_choices = [(d[1], d[1]) for d in date_choices]
    return date_choices


class ContactForm(forms.Form):
    first_name = forms.CharField(
        max_length=255, required=True,
        initial='',
        widget=forms.TextInput(
            attrs={'class': 'form-control'})
    )

    last_name = forms.CharField(
        max_length=255, required=True,
        initial='',
        widget=forms.TextInput(
            attrs={'class': 'form-control'})
    )

    email_address = forms.EmailField(
        max_length=255,
        required=True,
        widget=forms.TextInput(
            attrs={'class': 'form-control'})
    )

    subject = forms.ChoiceField(
        required=True,
        label="What can we help you with?",
        choices=(
            ('Membership Enquiry', 'Membership Enquiry'),
            ('Class Booking Enquiry', 'Class Booking Enquiry'),
            ('Private Booking', 'Private Booking Enquiry'),
            ('Personal Training', 'PT Enquiry'),
            ('General Enquiry', 'General Enquiry')
        ),
        widget=forms.Select(attrs={'class': 'form-control input-xs disabled'})
    )

    cc = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={
            'class': "regular-checkbox",
            'id': 'cc_id'
        }),
        label="Send me a copy of my email request",
        initial=True,
        required=False
    )

    message = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control email-message',
                                     'rows': 10}),
        label='Message',
        required=True)

    data_privacy_accepted = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={
            'class': "regular-checkbox",
            'id': 'data_privacy_accepted_id'
        }),
        label=mark_safe(
            "I confirm I have reviewed and accept the terms of the "
            "<a href='/data-privacy-policy'>data privacy policy</a>"
        ),
        required=False
    )

    def clean_data_privacy_accepted(self):
        # We hide the checkbox in order to style it, so we need to validate
        # on the backend instead of relying on the browser to do it
        accepted = self.cleaned_data.get('data_privacy_accepted', False)
        if not accepted:
            self.add_error(
                'data_privacy_accepted',
                'Please confirm you accept the terms of the data privacy '
                'agreement before submitting your request'
            )
        else:
            return accepted
