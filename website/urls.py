from django.conf.urls import patterns, url
from django.views.generic import RedirectView

from website.views import TimetableListView

urlpatterns = patterns(
    'website.views',
    url(r'^about/$', 'about', name='about'),
    url(r'^classes/$', 'classes', name='classes'),
    url(r'^(?P<session_pk>\d+)/book/$', 'booking_request',
        name='booking_request'),
    url(r'^instructors/$', 'instructors', name='instructors'),
    url(r'^venues/$', 'venues', name='venues'),
    url(r'^membership/$', 'membership', name='membership'),
    url(r'^parties/$', 'parties', name='parties'),
    url(r'^gallery/$', 'gallery', name='gallery'),
    url(r'^contact-form/$', 'contact_form', name='contact_form'),
    url(r'^contact/$', 'contact', name='contact'),
    url(r'^timetable/$', TimetableListView.as_view(), name='timetable'),
    url(r'^polefit_admin_help/help/$',           'admin_help_login', name='admin_help_login'),
    url(r'^polefit_admin_help/help/sessions/$',           'admin_help_sessions', name='admin_help_sessions'),
    url(r'^polefit_admin_help/help/sessiontypes/$',           'admin_help_sessiontypes', name='admin_help_sessiontypes'),
    url(r'^polefit_admin_help/help/instructors/$',           'admin_help_instructors', name='admin_help_instructors'),
    url(r'^polefit_admin_help/help/venues/$',           'admin_help_venues', name='admin_help_venues'),
    url(r'^polefit_admin_help/help/gallery/$',           'admin_help_gallery', name='admin_help_gallery'),
    url(r'^polefit_admin_help/help/about/$',           'admin_help_about', name='admin_help_about'),
    url(r'^polefit_admin_help/help/events/$',           'admin_help_events', name='admin_help_events'),
    url(r'^$', RedirectView.as_view(url='/about/', permanent=True)),
)
