from django.conf.urls import patterns, url

urlpatterns = patterns(
    'polefit.website.views',
    url(r'^$',                  'index', name='index'),
    url(r'^about$',             'about', name='about'),
    url(r'^(?P<session_type_id>\d+)/classes/$', 'classes', name='classes'),
    url(r'^(?P<instructor_id>\d+)/instructor/$', 'instructor_info', name='instructor_info'),
    url(r'^instructors$',       'instructors', name='instructors'),
    url(r'^events$',       'events', name='events'),
    url(r'^venues$',            'venues', name='venues'),
    url(r'^booking$',           'booking', name='booking'),
    url(r'^gallery$',           'gallery', name='gallery'),
    url(r'^timetable',           'timetable', name='timetable'),
    url(r'^(?P<session_type_id>\d+)/classes/sessions/$', 'sessions_by_type', name='sessions_by_type'),
)
