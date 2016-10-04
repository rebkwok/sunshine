from django.conf.urls import url
from django.views.generic import RedirectView


from booking.views import EventListView, EventDetailView, BookingCreateView, \
    already_cancelled, already_paid, \
    BookingListView, \
    BookingHistoryListView, BookingUpdateView, \
    BookingDeleteView, update_booking_cancelled, \
    cancellation_period_past, duplicate_booking, fully_booked

urlpatterns = [
    url(r'^my-bookings/$', BookingListView.as_view(), name='bookings'),
    url(r'^booking-history/$', BookingHistoryListView.as_view(),
        name='booking_history'),
    url(r'^my-bookings/update/(?P<pk>\d+)/$', BookingUpdateView.as_view(),
        name='update_booking'),
    url(r'^my-bookings/update/(?P<pk>\d+)/cancelled/$',
        update_booking_cancelled,
        name='update_booking_cancelled'),
    url(r'^my-bookings/update/(?P<pk>\d+)/paid/$',
        already_paid, name='already_paid'),
    url(r'^my-bookings/cancel/(?P<pk>\d+)/$', BookingDeleteView.as_view(),
        name='delete_booking'),
    url(r'^my-bookings/cancel/(?P<pk>\d+)/already_cancelled/$',
        already_cancelled,
        name='already_cancelled'),
    url(r'^workshops/(?P<event_slug>[\w-]+)/cancellation-period-past/$',
        cancellation_period_past, name='cancellation_period_past'),
    url(r'^workshops/(?P<event_slug>[\w-]+)/duplicate/$',
        duplicate_booking, name='duplicate_booking'),
    url(r'^workshops/(?P<event_slug>[\w-]+)/full/$', fully_booked,
        name='fully_booked'),
    url(r'^workshops/(?P<event_slug>[\w-]+)/book/$', BookingCreateView.as_view(),
        name='book_event'),
    url(
        r'^workshops/(?P<slug>[\w-]+)/$', EventDetailView.as_view(),
        name='event_detail'
    ),
    url(
        r'^workshops/$', EventListView.as_view(),
        name='events'
    ),
    url(r'^$', RedirectView.as_view(url='workshops/', permanent=True)),
 ]
