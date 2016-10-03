import datetime
from django import forms
from django.conf import settings
from django.utils import timezone

from timetable.models import SessionType, TimetableSession, Venue


def get_session_types():

    def callable():
        SESSION_TYPE_CHOICES = list(
            TimetableSession.objects.select_related(
                'venue', 'session_type', 'membership_level'
            ).distinct()
                .values_list('session_type__index', 'session_type__name')
        )
        SESSION_TYPE_CHOICES.insert(0, (0, 'All class types'))
        return tuple(sorted(SESSION_TYPE_CHOICES))

    return callable


def get_venues():

    def callable():
        VENUE_CHOICES = list(
            TimetableSession.objects.select_related(
                'venue', 'session_type', 'membership_level'
            ).distinct()
                .values_list('venue__abbreviation', 'venue__abbreviation')
        )
        VENUE_CHOICES.insert(0, ('', 'All locations'))
        return tuple(VENUE_CHOICES)

    return callable


class TimetableFilter(forms.Form):
    filtered_session_type = forms.ChoiceField(
        choices=get_session_types(),
        widget=forms.Select(attrs={'class': 'form-control input-xs'})
    )

    filtered_venue = forms.ChoiceField(
        choices=get_venues(),
        widget=forms.Select(attrs={'class': 'form-control input-xs'})
    )


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
    days_ahead = day - timezone.now().weekday()
    if days_ahead < 0:  # Target day already happened this week
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
            ('Party Booking', 'Party Booking'),
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


class BookingRequestForm(ContactForm):

    def __init__(self, *args, **kwargs):
        self.session = kwargs.pop('session')
        super(BookingRequestForm, self).__init__(*args, **kwargs)

        del self.fields['subject']
        del self.fields['message']

        self.fields['date'] = forms.ChoiceField(
            choices=get_dates(self.session),
            label="Date you wish to book for:",
            help_text="Please note regular weekly bookings are only "
                      "available if you have a monthly membership"
        )

        self.fields['additional_message'] = forms.CharField(
            widget=forms.Textarea(attrs={'class': 'form-control email-message',
                                         'rows': 10}),
            label='Additional comments',
            required=False)
