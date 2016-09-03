from django.conf.urls import include, url

from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    url(r'', include('website.urls', namespace='website')),
    url(r'^accounts/', include('accounts.urls', namespace='accounts')),
    url(r'^accounts/', include('allauth.urls')),
    url(r'^grappelli/', include('grappelli.urls')), # grappelli URLS
    url(r'^pf_admin/',     include(admin.site.urls)),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
