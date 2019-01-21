from datetime import datetime
import logging
import pytz

from collections import OrderedDict

from django.shortcuts import HttpResponseRedirect, render, get_object_or_404
from django.views.generic import ListView, DetailView
from django.utils import timezone
from django.utils.safestring import mark_safe

from booking.forms import EventsFilter
from booking.models import Booking, Event, WaitingListUser


logger = logging.getLogger(__name__)


DAYS = OrderedDict((
    ('01MO', 'Monday'),
    ('02TU', 'Tuesday'),
    ('03WE', 'Wednesday'),
    ('04TH', 'Thursday'),
    ('05FR', 'Friday'),
    ('06SA', 'Saturday'),
    ('07SU', 'Sunday')
))


class EventListView(ListView):
    model = Event
    context_object_name = 'events'
    template_name = 'booking/regular_classes.html'

    def get_queryset(self):
        self.event_type = self.request.GET.get('type', 'regular_session')
        self.event_name = self.request.GET.get('name', 'all')
        self.venue = self.request.GET.get('venue', 'all')
        self.event_day = self.request.GET.get('day')
        self.event_time = self.request.GET.get('time')

        # show all future events for staff users
        if self.request.user.is_staff:
            events = Event.objects.filter(
                event_type=self.event_type, date__gte=timezone.now()
            ).order_by('date')
        else:
            events = Event.objects.filter(
                event_type=self.event_type, date__gte=timezone.now(), show_on_site=True
            ).order_by('date')

        if self.event_name != 'all':
            events = events.filter(name=self.event_name)
        if self.venue != 'all':
            events = events.filter(venue__abbreviation=self.venue)

        # select day/time
        if self.event_day in DAYS.keys() and self.event_time:
            weekday = list(DAYS.keys()).index(self.event_day)
            try:
                event_time = self.event_time.split(':')
                hour = int(event_time[0])
                min = int(event_time[1])
            except (ValueError, IndexError):
                self.event_time = None
            else:

                localtz = pytz.timezone('Europe/London')
                event_ids = [
                    event.id for event in events if event.date.weekday() == weekday
                    and event.date.minute == min
                    and event.date.hour == hour - (event.date.astimezone(localtz).dst().seconds / 3600)
                ]
                events = events.filter(id__in=event_ids)
        return events

    def get_context_data(self, **kwargs):
        queryset = self.object_list
        # Call the base implementation first to get a context
        context = super(EventListView, self).get_context_data(**kwargs)
        context['section'] = 'events'
        if not self.request.user.is_anonymous:
            # Add in the booked_events
            user_booked_events = Booking.objects.select_related()\
                .filter(user=self.request.user, status='OPEN', no_show=False)\
                .values_list('event__id', flat=True)
            booked_events = queryset.filter(id__in=user_booked_events).values_list('id', flat=True)
            waiting_list_events = WaitingListUser.objects\
                .filter(user=self.request.user)\
                .values_list('event__id', flat=True)
            context['booked_events'] = booked_events
            context['waiting_list_events'] = waiting_list_events
        if self.request.user.is_staff:
            # add in the staff-only events
            context['staff_only_events'] = queryset.filter(
                show_on_site=False
            ).values_list('id', flat=True)

        context['workshops_available_to_book'] = Event.objects.filter(
            event_type='workshop', date__gte=timezone.now()
        ).exists()
        context['classes_available_to_book'] = Event.objects.filter(
            event_type='regular_session', date__gte=timezone.now()
        ).exists()

        form = EventsFilter(
            event_type=self.event_type,
            initial={'name': self.event_name, 'venue': self.venue}
        )

        context['form'] = form
        context['name'] = self.event_name
        context['day'] = DAYS.get(self.event_day, None)
        context['venue'] = self.venue
        context['time'] = self.event_time
        return context

    def get_template_names(self):
        # event_type = self.request.GET.get('type', 'regular_session')
        if self.event_type == 'workshop':
            return 'booking/events.html'
        else:
            return self.template_name


class EventDetailView(DetailView):

    model = Event
    context_object_name = 'event'
    template_name = 'booking/event.html'

    def get_object(self):
        if self.request.user.is_staff:
            return get_object_or_404(Event, slug=self.kwargs['slug'])
        return get_object_or_404(
            Event, slug=self.kwargs['slug'], show_on_site=True
        )

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(EventDetailView, self).get_context_data()
        event = self.object
        event_type = 'workshop'
        user = self.request.user

        context['event_type'] = event_type

        if event.date <= timezone.now():
            context['past'] = True

        # booked/cancelled flags
        if not self.request.user.is_anonymous:
            booked = False
            cancelled = False
            try:
                existing_booking = Booking.objects.get(event=event, user=user)
            except Booking.DoesNotExist:
                existing_booking = None

            if existing_booking:
                if existing_booking.status == 'OPEN':
                    if existing_booking.no_show:
                        cancelled = True
                    else:
                        booked = True
                else:
                    cancelled = True

            # waiting_list flag
            try:
                WaitingListUser.objects.get(user=user, event=event)
                context['waiting_list'] = True
            except WaitingListUser.DoesNotExist:
                pass

            # booking info text and bookable
            booking_info_text = ''
            context['bookable'] = event.bookable
            if booked:
                context['bookable'] = False
                booking_info_text = "You have booked for this " \
                                    "{}.".format(event_type)
                context['booked'] = True
            else:
                if cancelled:
                    context['cancelled'] = True
                    cancelled_text = "You have previously booked " \
                                                  "for this {} and your booking " \
                                                  "has been " \
                                                  "cancelled.".format(event_type)
                    context['booking_info_text_cancelled'] = cancelled_text

                if event.spaces_left <= 0:
                    booking_info_text = "This {} is now full.".format(event_type)
        else:
            login_url_str = "/accounts/login?next=/booking/{}s/{}".format(
                event_type, event.slug
            )
            if event.spaces_left <= 0:
                booking_info_text = mark_safe(
                    "This {} is now full.  "
                    "Please <a href='{}'>log in</a> to join the waiting "
                    "list.".format(event_type, login_url_str)
                )
            else:
                booking_info_text = mark_safe(
                    "Please <a href='{}'>log in</a> to book.".format(
                        login_url_str
                    )
                )
        context['booking_info_text'] = booking_info_text
        return context
