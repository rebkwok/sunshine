from django.shortcuts import render

from booking.views.ajax_views import booking_details, toggle_booking, \
    toggle_waiting_list, update_booking_count, ajax_cart_item_delete
from booking.views.event_views import EventDetailView, RegularClassesEventListView, \
    WorkshopEventListView, PrivateClassesEventListView
from booking.views.booking_views import BookingHistoryListView, BookingListView
from booking.views.shopping_basket import shopping_basket_view, guest_shopping_basket, \
    stripe_checkout, check_total
from booking.views.misc import csrf_failure

__all__ = [
    'RegularClassesEventListView', 'WorkshopEventListView', 'EventDetailView', 
    'BookingListView',
    'BookingHistoryListView', 'PrivateClassesEventListView',
    'booking_details', 'toggle_booking', 'toggle_waiting_list', 'update_booking_count',
    'shopping_basket_view', 'guest_shopping_basket', 'stripe_checkout', 'check_total',
    'ajax_cart_item_delete',
    'csrf_failure'
]


def permission_denied(request):
    return render(request, 'booking/permission_denied.html')