from functools import wraps

from django.views.generic import ListView
from django.urls import reverse
from django.shortcuts import HttpResponseRedirect

from timetable.models import TimetableSession, Venue
from timetable.forms import TimetableFilter


def superuser_required(func):
    def decorator(request, *args, **kwargs):
        if request.user.is_superuser:
            return func(request, *args, **kwargs)
        else:
            return HttpResponseRedirect(reverse('permission_denied'))
    return wraps(func)(decorator)


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
        venue = self.request.GET.get('filtered_venue', 'all')

        if session_type != 0:
            queryset = queryset.filter(session_type__id=session_type)
        if venue != 'all':
            queryset = queryset.filter(venue__abbreviation=venue)

        return queryset

    def get_context_data(self, *args, **kwargs):
        # Call the base implementation first to get a context
        context = super(TimetableListView, self).get_context_data(**kwargs)
        context['section'] = 'timetable'
        context['venues'] = Venue.objects.all()

        session_type = self.request.GET.get('filtered_session_type', 0)
        session_type = int(session_type)
        venue = self.request.GET.get('filtered_venue', 'all')

        form = TimetableFilter(
            initial={
                'filtered_session_type': session_type, 'filtered_venue': venue
            }
        )

        context['form'] = form
        return context
