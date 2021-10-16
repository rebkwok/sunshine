from django.urls import path

from website.views import home, \
    contact, \
    contact_form, venues

app_name = 'website'

urlpatterns = [
    path('', home, name='home'),
    path('venues/', venues, name='venues'),
    path('contact-form/', contact_form, name='contact_form'),
    path('contact/', contact, name='contact'),
]
