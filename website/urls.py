from django.conf.urls import url
from django.views.generic import RedirectView

from website.views import about, \
    booking_request, classes, contact, \
    contact_form, instructors, \
    membership, parties, TimetableListView, venues

urlpatterns = [
    url(r'^about/$', about, name='about'),
    url(r'^classes/$', classes, name='classes'),
    url(r'^(?P<session_pk>\d+)/book/$', booking_request,
        name='booking_request'),
    url(r'^instructors/$', instructors, name='instructors'),
    url(r'^venues/$', venues, name='venues'),
    url(r'^membership/$', membership, name='membership'),
    url(r'^parties/$', parties, name='parties'),
    url(r'^contact-form/$', contact_form, name='contact_form'),
    url(r'^contact/$', contact, name='contact'),
    url(r'^timetable/$', TimetableListView.as_view(), name='timetable'),
    url(r'^$', RedirectView.as_view(url='/about/', permanent=True)),
]
