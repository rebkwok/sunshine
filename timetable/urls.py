from django.conf.urls import patterns, url

from timetable import views

urlpatterns = patterns('timetable.views',
    url(r'^$', views.index, name='index'),
    url(r'^instructors/$', views.instructors, name='instructors'),
    url(r'^(?P<instructor_id>\d+)/instructor/$', views.instructor_info, name='instructor'),
    url(r'^(?P<session_type_id>\d+)/classes/$', views.session_type_info, name='session_type_info'),
    url(r'^(?P<session_type_id>.+)/filtered_session/$', views.filtered_session_type, name='filtered_session'),
    )
