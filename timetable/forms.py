from datetime import datetime, date

from django import forms
from django.utils import timezone

from timetable.models import TimetableSession


def get_session_types():

    def callable():
        SESSION_TYPE_CHOICES = list(
            TimetableSession.objects.select_related(
                'venue', 'session_type'
            ).distinct().order_by('session_type__index')
            .values_list('session_type__id', 'session_type__name')
        )
        SESSION_TYPE_CHOICES.insert(0, (0, 'All class types'))
        return tuple(SESSION_TYPE_CHOICES)

    return callable


def get_venues():

    def callable():
        VENUE_CHOICES = list(
            TimetableSession.objects.select_related(
                'venue', 'session_type'
            ).distinct()
            .values_list('venue__abbreviation', 'venue__abbreviation')
        )
        VENUE_CHOICES.insert(0, ('all', 'All locations'))
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
    

class UploadTimetableForm(forms.Form):

    def __init__(self, *args, **kwargs):
        super(UploadTimetableForm, self).__init__(*args, **kwargs)

        qs = TimetableSession.objects.all().order_by('session_day', 'start_time')

        self.fields['start_date'] = forms.DateField(
            label="Start Date",
            widget=forms.DateInput(
                attrs={
                    'class': "form-control",
                    'id': 'datepicker_startdate',
                    'autocomplete': 'off'
                },
                format='%a %d %b %Y'
            ),
            required=True,
            initial=date.today()
        )

        self.fields['end_date'] = forms.DateField(
            label="End Date",
            widget=forms.DateInput(
                attrs={
                    'class': "form-control",
                    'id': 'datepicker_enddate',
                    'autocomplete': 'off'
                },
                format='%a %d %b %Y'
            ),
            required=True,
        )

        self.fields['show_on_site'] = forms.BooleanField(
            initial=True, help_text='(Classes will be available immediately for booking)',
            required=False
        )

        self.fields['sessions'] = forms.ModelMultipleChoiceField(
            widget=forms.CheckboxSelectMultiple(
                attrs={'class': 'select-checkbox'}
            ),
            label="Choose sessions to upload",
            queryset=qs,
            initial=TimetableSession.objects.values_list('id', flat=True),
            required=True
        )

    def clean(self):
        super(UploadTimetableForm, self).clean()
        cleaned_data = self.cleaned_data

        start_date = self.data.get('start_date')
        if start_date:
            if self.errors.get('start_date'):
                del self.errors['start_date']
            try:
                start_date = datetime.strptime(start_date, '%a %d %b %Y').date()
                if start_date >= timezone.now().date():
                    cleaned_data['start_date'] = start_date
                else:
                    self.add_error('start_date',
                                   'Must be in the future')
            except ValueError:
                self.add_error(
                    'start_date', 'Invalid date format.  Select from '
                                        'the date picker or enter date in the '
                                        'format e.g. Mon 08 Jun 2015')

        end_date = self.data.get('end_date')
        if end_date:
            if self.errors.get('end_date'):
                del self.errors['end_date']
            try:
                end_date = datetime.strptime(end_date, '%a %d %b %Y').date()
            except ValueError:
                self.add_error(
                    'end_date', 'Invalid date format.  Select from '
                                        'the date picker or enter date in the '
                                        'format ddd DD Mmm YYYY (e.g. Mon 15 Jun 2015)')

        if not self.errors.get('end_date') and not self.errors.get('start_date'):
            if end_date >= start_date:
                cleaned_data['end_date'] = end_date
            else:
                self.add_error('end_date',
                                   'Cannot be before start date')
        return cleaned_data
