import logging
import pytz

from collections import OrderedDict

from django.shortcuts import HttpResponseRedirect, render, get_object_or_404
from django.views.generic import ListView, DetailView
from django.urls import reverse
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.http import Http404
from booking.email_helpers import email_waiting_lists

from booking.forms import EventsFilter
from booking.models import Booking, Event, WaitingListUser
from booking.utils import host_from_request


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


class BaseEventListView(ListView):
    model = Event
    context_object_name = 'events'    
    template_name = 'booking/events_list.html'
    paginate_by = 20
    
    def dispatch(self, request, *args, **kwargs):
        # Cleanup bookings so user is looking at current availability
        event_ids_from_expired_bookings = Booking.cleanup_expired_bookings(use_cache=True)
        email_waiting_lists(event_ids_from_expired_bookings, host=host_from_request(request))
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        name = self.request.GET.get('name', 'all').strip()
        level = self.request.GET.get('level')
        if name and level:
            self.event_name = '{} ({})'.format(name, level.strip())
        else:
            self.event_name = name
        self.event_day = self.request.GET.get('day', '').strip()
        self.event_time = self.request.GET.get('time', '').strip()

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

    def paginate_queryset(self, queryset, page_size):
        """Paginate the queryset, if needed."""
        try:
            resp = super().paginate_queryset(queryset, page_size)
        except Http404:
            paginator = self.get_paginator(
                queryset, page_size, orphans=self.get_paginate_orphans(),
                allow_empty_first_page=self.get_allow_empty()
            )
            page = paginator.page(1)
            return paginator, page, page.object_list, page.has_other_pages()
        return resp

    def get_context_data(self, **kwargs):
        queryset = self.object_list
        # Call the base implementation first to get a context
        context = super().get_context_data(**kwargs)
        context['section'] = 'booking'
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

        alternative_events = Event.objects.exclude(event_type=self.event_type).filter(
            date__gte=timezone.now(), cancelled=False
        )

        if not self.request.user.is_staff:
            alternative_events = alternative_events.filter(show_on_site=True)

        context['workshops_available_to_book'] = alternative_events.filter(event_type="workshop").exists()
        context['classes_available_to_book'] = alternative_events.filter(event_type="regular_session").exists()
        context['privates_available_to_book'] = alternative_events.filter(event_type="private").exists()

        context['event_type'] = self.event_type_hr
        context['event_type_plural'] = self.event_type_plural

        form = EventsFilter(
            event_type=self.event_type,
            initial={'name': self.event_name}
        )

        context['form'] = form
        context['name'] = self.event_name
        context['day'] = DAYS.get(self.event_day, None)
        context['time'] = self.event_time

        context["all_events_url"] = reverse(f"booking:{self.event_type}_list")

        # TODO: Tabs per location
        # # paginate each queryset
        # # tab = self.request.GET.get('tab', 0)

        # # try:
        # #     tab = int(tab)
        # # except ValueError:  # value error if tab is not an integer, default to 0
        # #     tab = 0

        # # context['tab'] = str(tab)

        # # if not tab or tab == 0:
        # #     page = self.request.GET.get('page', 1)
        # # else:
        # #     page = 1
        # page = self.request.GET.get('page', 1)
        # all_paginator = Paginator(all_events, 30)

        # queryset = all_paginator.get_page(page)
        # location_events = [{
        #     'index': 0,
        #     'queryset': queryset,
        #     'location': 'All locations',
        #     'paginator_range': queryset.paginator.get_elided_page_range(queryset.number)
        # }]
        # # NOTE: this is unnecessary since we only have one location; leaving it in in case there is ever another studio to add
        # # for i, location in enumerate([lc[0] for lc in Event.LOCATION_CHOICES], 1):
        # #     location_qs = all_events.filter(location=location)
        # #     if location_qs:
        # #         # Don't add the location tab if there are no events to display
        # #         location_paginator = Paginator(location_qs, 30)
        # #         if tab and tab == i:
        # #             page = self.request.GET.get('page', 1)
        # #         else:
        # #             page = 1
        # #         queryset = location_paginator.get_page(page)
        # #
        # #         location_obj = {
        # #             'index': i,
        # #             'queryset': queryset,
        # #             'location': location
        # #         }
        # #         location_events.append(location_obj)
        # context['location_events'] = location_events

        return context


class RegularClassesEventListView(BaseEventListView):

    @property
    def event_type(self):
        return "regular_session"

    @property
    def event_type_hr(self):
        return "class"
    
    @property
    def event_type_plural(self):
        return "classes"


class PrivateClassesEventListView(RegularClassesEventListView):

    @property
    def event_type(self):
        return "private"

    @property
    def event_type_hr(self):
        return "private"
    
    @property
    def event_type_plural(self):
        return "private lessons"


class WorkshopEventListView(BaseEventListView):

    @property
    def event_type(self):
        return "workshop"

    @property
    def event_type_hr(self):
        return "workshop"
    
    @property
    def event_type_plural(self):
        return "workshops"


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
        event_type = 'class' if event.event_type == 'regular_session' else 'workshop'
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
