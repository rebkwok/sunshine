# -*- coding: utf-8 -*-
import logging
from urllib.parse import urlencode

from django.http import HttpResponse
from django.shortcuts import HttpResponseRedirect
from django.urls import reverse
from django.views.generic import ListView, DeleteView
from django.utils import timezone
from braces.views import LoginRequiredMixin

from booking.models import Booking, WaitingListUser
from .booking_helpers import cancel_booking_from_view
from .views_utils import DataPolicyAgreementRequiredMixin


logger = logging.getLogger(__name__)


class BookingListView(DataPolicyAgreementRequiredMixin, LoginRequiredMixin, ListView):

    model = Booking
    context_object_name = 'bookings'
    template_name = 'booking/bookings.html'
    paginate_by = 20

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


class BookingDeleteView(
    DataPolicyAgreementRequiredMixin, LoginRequiredMixin, DeleteView
):
    model = Booking
    success_message = 'Booking cancelled for {}.'

    def dispatch(self, request, *args, **kwargs):
        booking = self.get_object()
        if booking.status == 'CANCELLED':
            # redirect if already cancelled
            return HttpResponseRedirect(
                reverse(f'booking:{booking.event.event_type}_list')
                )
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super().get_context_data(**kwargs)
        booking = self.get_object()
        # Add in the event
        context['event'] = booking.event
        # Add in membership info
        context['booked_with_membership'] = booking.user_membership is not None
        context['membership_booked_within_allowed_time'] = booking.booked_with_membership_within_allowed_time()
        context['booking'] = booking
        return context

    def form_valid(self, _form):
        booking = self.get_object()
        # cancel, process refunds etc, email users, email waiting list
        cancel_booking_from_view(self.request, booking)
        
        if self.request.POST.get('ref') == 'basket':
            # deleting from shopping basket, just return
            return HttpResponse('Booking cancelled')

        # deleting from events list or bookings
        next_page = self.request.GET.get('next') or self.request.POST.get('next')
        params = {}
        for param in ["name_filter", "venue_filter", "page"]:
            if param in self.request.POST:
                params[param] = self.request.POST[param]

        url = self.get_success_url(next_page)
        if params:
            url += '?{}'.format(urlencode(params))
        return HttpResponseRedirect(url)

    def get_success_url(self, next_page=None):
        if next_page:
            return reverse('booking:{}'.format(next_page))
        return reverse('booking:bookings')

