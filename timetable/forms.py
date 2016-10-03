from django import forms

from timetable.models import TimetableSession


def get_session_types():

    def callable():
        SESSION_TYPE_CHOICES = list(
            TimetableSession.objects.select_related(
                'venue', 'session_type', 'membership_level'
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