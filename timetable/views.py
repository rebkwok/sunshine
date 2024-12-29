from django.views.generic import ListView

from timetable.models import TimetableSession, Venue
from timetable.forms import TimetableFilter


class TimetableListView(ListView):
    model = TimetableSession
    context_object_name = 'timetable_sessions'
    template_name = 'timetable/timetable.html'

    def get_queryset(self):
        queryset = (
            TimetableSession.objects
            .filter(show_on_timetable_page=True)
            .select_related('venue', 'session_type')
            .order_by('session_day', 'start_time', 'venue')
        )
        
        session_type = self.request.GET.get('filtered_session_type', 0)
        session_type = int(session_type)

        if session_type != 0:
            queryset = queryset.filter(session_type__id=session_type)

        return queryset

    def _get_tab(self):
        tab = self.request.GET.get('tab', 0)

        try:
            tab = int(tab)
        except ValueError:  # value error if tab is not an integer, default to 0
            tab = 0
        
        return tab

    def get_context_data(self, *args, **kwargs):
        # Call the base implementation first to get a context
        context = super(TimetableListView, self).get_context_data(**kwargs)
        context['section'] = 'timetable'

        session_type = self.request.GET.get('filtered_session_type', 0)
        session_type = int(session_type)

        tab = self._get_tab()
        context['tab'] = str(tab)

        form = TimetableFilter(
            initial={'filtered_session_type': session_type}
        )

        context['form'] = form

        queryset = self.get_queryset()
        
        location_events = []
        for index, location_choice in Venue.location_choices().items():
            if index != 0:
                queryset = queryset.filter(venue__location=location_choice)
            if queryset:
                # only add location if there are events to display
                location_events.append(
                    {
                        "index": index,
                        "queryset": queryset,
                        "location": location_choice
                    }
                )

        context['location_events'] = location_events

        return context
