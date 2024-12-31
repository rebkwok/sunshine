from django.urls import path

from website.views import demo, home, contact, contact_form, faq

app_name = 'website'

urlpatterns = [
    path('', home, name='home'),
    path('contact-form/', contact_form, name='contact_form'),
    path('contact/', contact, name='contact'),
    path('faq/', faq, name='faq'),
    path('demo/', demo)
]
