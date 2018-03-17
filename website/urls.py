from django.urls import path
from django.views.generic import RedirectView

from website.views import about, \
    booking_request, classes, contact, \
    contact_form, instructors, \
    membership, parties, venues

app_name = 'website'

urlpatterns = [
    path('about/', about, name='about'),
    path('classes/', classes, name='classes'),
    path('<int:session_pk>/book/', booking_request,
        name='booking_request'),
    path('instructors/', instructors, name='instructors'),
    path('venues/', venues, name='venues'),
    path('membership/', membership, name='membership'),
    path('parties/', parties, name='parties'),
    path('contact-form/', contact_form, name='contact_form'),
    path('contact/', contact, name='contact'),
    path('', RedirectView.as_view(url='/about/', permanent=True)),
]
