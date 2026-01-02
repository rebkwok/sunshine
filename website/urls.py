from django.conf import settings
from django.urls import path

from website.views import home, home_legacy, contact, faq, session_types, venues

app_name = 'website'

urlpatterns = [
    path('contact/', contact, name='contact'),
    path('faq/', faq, name='faq'),
    path("what-we-offer/", session_types, name="session_types"),
    path("venues/", venues, name="venues"),
]

if settings.LEGACY_HOMEPAGE:
    urlpatterns.insert(0, path('', home_legacy, name='home'))
else:
    urlpatterns.insert(0, path('', home, name='home'))
