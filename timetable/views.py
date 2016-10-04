from django.views.generic import ListView

from timetable.models import TimetableSession, Venue
from timetable.forms import TimetableFilter


class TimetableListView(ListView):
    model = TimetableSession
    context_object_name = 'timetable_sessions'
    template_name = 'timetable/timetable.html'

    def get_queryset(self):

        queryset = TimetableSession.objects.select_related(
            'venue', 'session_type'
        ).order_by(
                'session_day', 'start_time', 'venue'
        )
        session_type = self.request.GET.get('filtered_session_type', 0)
        session_type = int(session_type)
        venue = self.request.GET.get('filtered_venue', '')

        if session_type != 0:
            queryset = queryset.filter(session_type__id=session_type)
        if venue != '':
            queryset = queryset.filter(venue__abbreviation=venue)

        return queryset

    def get_context_data(self, *args, **kwargs):
        # Call the base implementation first to get a context
        context = super(TimetableListView, self).get_context_data(**kwargs)
        context['section'] = 'timetable'
        context['venues'] = Venue.objects.all()

        session_type = self.request.GET.get('filtered_session_type', 0)
        session_type = int(session_type)
        venue = self.request.GET.get('filtered_venue', '')

        form = TimetableFilter(
            initial={
                'filtered_session_type': session_type, 'filtered_venue': venue
            }
        )

        context['form'] = form
        return context
