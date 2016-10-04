import logging

from django.db.models import Q
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import HttpResponseRedirect, render, get_object_or_404
from django.views.generic import ListView, DetailView
from django.utils import timezone
from braces.views import LoginRequiredMixin

from booking.models import Booking, Event, WaitingListUser


logger = logging.getLogger(__name__)


class EventListView(ListView):
    model = Event
    context_object_name = 'events'
    template_name = 'booking/events.html'

    def get_queryset(self):
        # show all future events for staff users
        if self.request.user.is_staff:
            return Event.objects.filter(
                date__gte=timezone.now()
            ).order_by('date')
        return Event.objects.filter(
            date__gte=timezone.now(), show_on_site=True
        ).order_by('date')

    def get_context_data(self, **kwargs):
        queryset = self.get_queryset()
        # Call the base implementation first to get a context
        context = super(EventListView, self).get_context_data(**kwargs)
        context['section'] = 'events'
        if not self.request.user.is_anonymous():
            # Add in the booked_events
            user_booked_events = Booking.objects.select_related()\
                .filter(user=self.request.user, status='OPEN', no_show=False)\
                .values_list('event__id', flat=True)
            booked_events = queryset.filter(
                id__in=user_booked_events
            ).values_list('id', flat=True)
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

        return context


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
        if not self.request.user.is_anonymous():
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
            if event.spaces_left <= 0:
                booking_info_text = "This {} is now full.  Please log in to " \
                                    "join the waiting list.".format(event_type)
            else:
                booking_info_text = "Please log in to book."
        context['booking_info_text'] = booking_info_text
        return context
