from django.conf.urls import patterns, url

urlpatterns = patterns(
    'polefit.website.views',
    url(r'^booking$', 'booking', name='booking'),
    url(r'^about$',    'about', name='about'),
    url(r'^instructors$',    'about', name='instructors'),
)
