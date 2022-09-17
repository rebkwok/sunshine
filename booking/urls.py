from django.urls import path
from django.views.generic import RedirectView


from booking.views import RegularClassesEventListView, WorkshopEventListView, \
    EventDetailView, PrivateClassesEventListView, \
    BookingListView, BookingHistoryListView, BookingDeleteView, \
    toggle_booking, toggle_waiting_list, booking_details, update_booking_count, \
    shopping_basket_view

app_name = 'booking'


urlpatterns = [
    path('my-bookings/', BookingListView.as_view(), name='bookings'),
    path('booking-history/', BookingHistoryListView.as_view(),
        name='booking_history'),
    path('classes', RegularClassesEventListView.as_view(), name="regular_session_list"),
    path('privates', PrivateClassesEventListView.as_view(), name="private_list"),
    path('workshops', WorkshopEventListView.as_view(), name="workshop_list"),
    path(
        'event/<slug:slug>/', EventDetailView.as_view(),
        name='event_detail'
    ),
    path(
        'booking/<int:pk>/delete/',
        BookingDeleteView.as_view(), name='delete_booking'
    ),
    path(
        'toggle-booking/<int:event_id>/',
        toggle_booking, name='toggle_booking'
    ),
    path(
        'ajax-toggle-waiting-list/<int:event_id>/',
        toggle_waiting_list, name='toggle_waiting_list'
    ),
    path(
        'update-booking-details/<int:event_id>/',
        booking_details, name='booking_details'
    ),
    path(
        'ajax-update-booking-count/<int:event_id>/',
        update_booking_count, name='update_booking_count'
    ),
        path(
        'booking/shopping-basket/',
        shopping_basket_view, name='shopping_basket'
    ),
    path('', RedirectView.as_view(url='/classes/', permanent=True)),
]
