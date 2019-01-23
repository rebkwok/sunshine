from functools import wraps

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.views.generic import ListView
from django.urls import reverse
from django.shortcuts import HttpResponseRedirect

from timetable.models import TimetableSession, Venue
from timetable.forms import TimetableFilter, UploadTimetableForm
from timetable.utils import upload_timetable


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


@login_required
@superuser_required
def upload_timetable_view(request,
                          template_name="timetable/upload_timetable_form.html"):

    if request.method == 'POST':
        form = UploadTimetableForm(request.POST)
        if form.is_valid():
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
            session_ids = form.cleaned_data['sessions']
            show_on_site = form.cleaned_data['show_on_site']

            created_classes, existing_classes, duplicate_classes = upload_timetable(
                start_date, end_date, session_ids, show_on_site, request.user
            )
            context = {'start_date': start_date,
                       'end_date': end_date,
                       'created_classes': created_classes,
                       'existing_classes': existing_classes,
                       'duplicate_classes': duplicate_classes,
                       'sidenav_selection': 'upload_timetable'}
            return render(
                request, 'timetable/upload_timetable_confirmation.html',
                context
            )

    else:
        form = UploadTimetableForm()

    return render(request, template_name, {'form': form})
