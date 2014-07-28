from django.conf.urls import patterns, include, url

from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static

admin.autodiscover()


urlpatterns = patterns('',
    url(r'',            include('polefit.website.urls', namespace='website')),
    (r'^grappelli/', include('grappelli.urls')), # grappelli URLS
    url(r'^pf_admin/',     include(admin.site.urls)),
    url(r'^timetable/', include('timetable.urls', namespace='timetable')),
) + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)