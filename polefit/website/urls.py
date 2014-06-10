from django.conf.urls import patterns, url

urlpatterns = patterns(
    'polefit.website.views',
    url(r'^$',                  'index', name='index'),
    url(r'^about$',             'about', name='about'),
    url(r'^classes_polefit$',   'classes_polefit', name='classes_polefit'),
    url(r'^classes_hoop$',      'classes_hoop', name='classes_hoop'),
    url(r'^classes_balletfit$', 'classes_balletfit', name='classes_balletfit'),
    url(r'^classes_bouncefit$', 'classes_bouncefit', name='classes_bouncefit'),
    url(r'^classes_stretch$',   'classes_stretch', name='classes_stretch'),
    url(r'^(?P<session_type_id>\d+)/classes/$', 'classes', name='classes'),
    url(r'^instructors$',       'instructors', name='instructors'),
    url(r'^venues$',            'venues', name='venues'),
    url(r'^booking$',           'booking', name='booking'),
    url(r'^gallery$',           'gallery', name='gallery'),
)
