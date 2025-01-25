from django.urls import path

from website.views import home, contact, contact_form, faq, session_types, venues

app_name = 'website'

urlpatterns = [
    path('', home, name='home'),
    path('contact-form/', contact_form, name='contact_form'),
    path('contact/', contact, name='contact'),
    path('faq/', faq, name='faq'),
    path("what-we-offer/", session_types, name="session_types"),
    path("venues/", venues, name="venues"),
]
