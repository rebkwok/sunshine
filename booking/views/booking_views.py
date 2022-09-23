# -*- coding: utf-8 -*-
import logging
from urllib.parse import urlencode

from django.http import HttpResponse
from django.shortcuts import HttpResponseRedirect
from django.urls import reverse
from django.views.generic import ListView, DeleteView
from django.utils import timezone
from braces.views import LoginRequiredMixin
from booking.email_helpers import email_waiting_lists

from booking.models import Booking, WaitingListUser
from booking.utils import host_from_request
from .views_utils import DataPolicyAgreementRequiredMixin


logger = logging.getLogger(__name__)


class BookingListView(DataPolicyAgreementRequiredMixin, LoginRequiredMixin, ListView):

    model = Booking
    context_object_name = 'bookings'
    template_name = 'booking/bookings.html'
    paginate_by = 20

    def dispatch(self, request, *args, **kwargs):
        # Cleanup bookings so user is looking at current availability
        event_ids_from_expired_bookings = Booking.cleanup_expired_bookings(use_cache=True)
        email_waiting_lists(event_ids_from_expired_bookings, host=host_from_request(request))
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return Booking.objects.filter(event__date__gte=timezone.now(), user=self.request.user).order_by('event__date')

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super().get_context_data(**kwargs)
        on_waiting_list = []
        can_cancel = []
        booking_status_display = {}

        for booking in self.object_list:

            if WaitingListUser.objects.filter(user=self.request.user, event=booking.event).exists():
                on_waiting_list.append(booking.id)

            if booking.event.can_cancel() and (booking.status == 'OPEN' and not booking.no_show):
                can_cancel.append(booking.id)

            booking_status_display[booking.id] = 'CANCELLED' if (booking.status == 'CANCELLED' or booking.no_show) else 'OPEN'
        context['on_waiting_list_booking_ids_list'] = on_waiting_list
        context['can_cancel_booking_ids_list'] = can_cancel
        context['booking_status_display'] = booking_status_display

        return context


class BookingHistoryListView(DataPolicyAgreementRequiredMixin, LoginRequiredMixin, ListView):

    model = Booking
    context_object_name = 'bookings'
    template_name = 'booking/bookings.html'
    paginate_by = 20

    def get_queryset(self):
        return Booking.objects.filter(event__date__gte=timezone.now(), user=self.request.user).order_by('event__date')

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super().get_context_data(**kwargs)

        booking_status_display = {
            booking.id: 'CANCELLED' if (booking.status == 'CANCELLED' or booking.no_show) else 'OPEN'
            for booking in self.object_list
        }
        context['booking_status_display'] = booking_status_display
        # Add in the history flag
        context['history'] = True

        return context
