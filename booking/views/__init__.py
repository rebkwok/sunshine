from django.shortcuts import render

from booking.views.ajax_views import booking_details, toggle_booking, \
    toggle_waiting_list, update_booking_count
from booking.views.event_views import EventDetailView, RegularClassesEventListView, \
    WorkshopEventListView, PrivateClassesEventListView
from booking.views.booking_views import BookingHistoryListView, BookingListView, BookingDeleteView
from booking.views.shopping_basket import shopping_basket_view

__all__ = [
    'RegularClassesEventListView', 'WorkshopEventListView', 'EventDetailView', 
    'BookingListView', 'BookingDeleteView',
    'BookingHistoryListView', 'PrivateClassesEventListView',
    'booking_details', 'toggle_booking', 'toggle_waiting_list', 'update_booking_count',
    'shopping_basket_view'
]


def permission_denied(request):
    return render(request, 'booking/permission_denied.html')