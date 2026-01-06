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

    def _get_location_data(self):
        active_locations = TimetableSession.active_locations()
        venue_locations = Venue.location_choices().items()

        if len(active_locations) > 1:
            default_tab = 0
        else:
            default_tab = next(k for k, v in venue_locations if v == active_locations[0])
        
        tab = self.request.GET.get('tab', default_tab)

        try:
            tab = int(tab)
        except ValueError:  # value error if tab is not an integer, default to 0
            tab = default_tab
        
        return tab, active_locations, venue_locations

    def get_context_data(self, *args, **kwargs):
        # Call the base implementation first to get a context
        context = super(TimetableListView, self).get_context_data(**kwargs)
        context['section'] = 'timetable'

        session_type = self.request.GET.get('filtered_session_type', 0)
        session_type = int(session_type)

        tab, active_locations, venue_locations = self._get_location_data()
        context['tab'] = tab

        form = TimetableFilter(
            initial={'filtered_session_type': session_type}
        )

        context['form'] = form

        all_queryset = self.get_queryset()
        
        location_events = []
        for index, location_choice in venue_locations:
            if index == 0 and len(active_locations) > 1:
                queryset = all_queryset
            elif location_choice not in active_locations:
                continue
            else:
                queryset = all_queryset.filter(venue__location__name=location_choice)

            location_events.append(
                {
                    "index": index,
                    "queryset": queryset,
                    "location": location_choice
                }
            )

        context['location_events'] = location_events

        return context
