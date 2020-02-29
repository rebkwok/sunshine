from django.urls import path


from booking.views import EventListView, EventDetailView, BookingCreateView, \
    already_cancelled, already_paid, \
    BookingListView, \
    BookingHistoryListView, BookingUpdateView, \
    BookingDeleteView, update_booking_cancelled, \
    cancellation_period_past, duplicate_booking, fully_booked, \
    toggle_booking, toggle_waiting_list, booking_details, update_booking_count, \
    outstanding_fees


app_name = 'booking'


urlpatterns = [
    path('my-bookings/', BookingListView.as_view(), name='bookings'),
    path('booking-history/', BookingHistoryListView.as_view(),
        name='booking_history'),
    path('my-bookings/update/<int:pk>/', BookingUpdateView.as_view(),
        name='update_booking'),
    path('my-bookings/update/<int:pk>/cancelled/',
        update_booking_cancelled,
        name='update_booking_cancelled'),
    path('my-bookings/update/<int:pk>/paid/',
        already_paid, name='already_paid'),
    path('my-bookings/cancel/<int:pk>/', BookingDeleteView.as_view(),
        name='delete_booking'),
    path('my-bookings/cancel/<int:pk>/already_cancelled/',
        already_cancelled,
        name='already_cancelled'),
    path('workshops/<slug:event_slug>/cancellation-period-past/',
        cancellation_period_past, name='cancellation_period_past'),
    path('workshops/<slug:event_slug>/duplicate/',
        duplicate_booking, name='duplicate_booking'),
    path('workshops/<slug:event_slug>/full/', fully_booked,
        name='fully_booked'),
    path('workshops/<slug:event_slug>/book/', BookingCreateView.as_view(),
        name='book_event'),
    path(
        'workshops/<slug:slug>/', EventDetailView.as_view(),
        name='event_detail'
    ),
    path('outstanding-fees/', outstanding_fees, name="outstanding_fees"),
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
    path('', EventListView.as_view(), name='events'),
 ]
