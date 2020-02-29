from django.shortcuts import render

from booking.views.ajax_views import booking_details, toggle_booking, \
    toggle_waiting_list, update_booking_count
from booking.views.event_views import EventDetailView, EventListView
from booking.views.booking_views import already_cancelled, already_paid, \
    BookingCreateView, BookingDeleteView, \
    BookingHistoryListView, BookingListView, BookingUpdateView, \
    duplicate_booking, update_booking_cancelled, fully_booked, \
    cancellation_period_past, outstanding_fees

__all__ = [
    'already_cancelled', 'already_paid',
    'EventListView', 'EventDetailView', 'BookingListView',
    'BookingHistoryListView', 'BookingCreateView', 'BookingUpdateView',
    'BookingDeleteView', 'duplicate_booking',
    'update_booking_cancelled',
    'fully_booked', 'cancellation_period_past',
    'booking_details', 'toggle_booking', 'toggle_waiting_list', 'update_booking_count',
    'outstanding_fees'
]


def permission_denied(request):
    return render(request, 'booking/permission_denied.html')