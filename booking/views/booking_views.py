# -*- coding: utf-8 -*-
import logging

from django.conf import settings
from django.urls import reverse
from django.views.generic import ListView
from django.utils import timezone
from braces.views import LoginRequiredMixin

from booking.models import Booking, WaitingListUser
from .views_utils import DataPolicyAgreementRequiredMixin


logger = logging.getLogger(__name__)


def get_paypal_dict(
        host, cost, item_name, invoice_id, custom,
        paypal_email=settings.DEFAULT_PAYPAL_EMAIL, quantity=1):

    paypal_dict = {
        "business": paypal_email,
        "amount": cost,
        "item_name": item_name,
        "custom": custom,
        "invoice": invoice_id,
        "currency_code": "GBP",
        "quantity": quantity,
        "notify_url": host + reverse('paypal-ipn'),
        "return": host + reverse('payments:paypal_confirm'),
        "cancel_return": host + reverse('payments:paypal_cancel'),

    }
    return paypal_dict


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
        paypalforms = {}
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
