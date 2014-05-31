from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()


urlpatterns = patterns('',
    url(r'',            include('polefit.website.urls')),
    url(r'^timetable', include('timetable.urls')),
    url(r'^admin/',     include(admin.site.urls)),
)
