from django.shortcuts import render

from booking.views.ajax_views import booking_details, toggle_booking, \
    toggle_waiting_list, update_booking_count
from booking.views.event_views import EventDetailView, RegularClassesEventListView, \
    WorkshopEventListView, PrivateClassesEventListView
from booking.views.booking_views import BookingHistoryListView, BookingListView

__all__ = [
    'RegularClassesEventListView', 'WorkshopEventListView', 'EventDetailView', 'BookingListView',
    'BookingHistoryListView', 'PrivateClassesEventListView',
    'booking_details', 'toggle_booking', 'toggle_waiting_list', 'update_booking_count',
]


def permission_denied(request):
    return render(request, 'booking/permission_denied.html')