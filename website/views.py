import random

from django.urls import reverse
from django.conf import settings
from django.shortcuts import render, HttpResponseRedirect
from django.contrib import messages
from django.utils.safestring import mark_safe

from booking.email_helpers import send_email
from timetable.models import Location, Venue, SessionType
from website.forms import ContactForm
from .models import GalleryImage, Testimonial, TeamMember


def home(request):
    images = GalleryImage.objects.filter(display_on_homepage=True)
    testimonials = list(Testimonial.objects.all())
    random.shuffle(testimonials)

    return render(
        request, 
        'website/home.html', 
        {
            'section': 'about',
            'gallery_images': images,
            'gallery_categories': set(images.values_list("category__name", flat=True)) - {None},
            'testimonials': testimonials,
            'team_members': TeamMember.objects.all()
        }
    )


def home_legacy(request):

    if "new-home-page" in request.GET:
        return home(request)

    class_types = SessionType.objects.filter(display_on_site=True)

    return render(request, 'website/home_legacy.html', {'section': 'home', 'class_types': class_types})


def faq(request):
    return render(request, 'website/faq.html', {'section': 'about'})


def process_contact_form(request, template_name):
    form = ContactForm(request.POST)

    if form.is_valid():
        subject = form.cleaned_data['subject']
        email_address = form.cleaned_data['email_address']
        first_name = form.cleaned_data['first_name']
        last_name = form.cleaned_data['last_name']
        cc = form.cleaned_data['cc']
        message = form.cleaned_data['message']

        ctx = {
                'first_name': first_name,
                'last_name': last_name,
                'email_address': email_address,
                'message': message,
            }

        send_email(
            request, subject, ctx,
            'website/email/contact_form_email.txt',
            template_html='website/email/contact_form_email.html',
            to_list=[settings.DEFAULT_STUDIO_EMAIL],
            cc_list=[email_address] if cc else [],
            reply_to_list=[email_address]
        )

        request.session['first_name'] = first_name
        request.session['last_name'] = last_name
        request.session['email_address'] = email_address
        # required field, so must be True if form valid
        request.session['data_privacy_accepted'] = True

        return_url = request.session.get(
            'return_url', reverse('website:contact')
        )
        messages.success(request, "Thanks for your enquiry!  Your email has been sent and we'll be in touch soon.")
        return HttpResponseRedirect(return_url)

    else:
        if form.non_field_errors():
            messages.error(
                request,
                mark_safe("There were errors in the following "
                          "fields: {}".format(form.non_field_errors())
                          )
            )
        else:
            messages.error(request, 'Please correct the errors below')
        return render(
            request, template_name, {'section': 'about', 'form': form}
        )


def contact(request, template_name='website/contact_us.html'):
    if request.method == 'POST':
        return process_contact_form(request, template_name)

    request.session['return_url'] = request.META.get(
        'HTTP_REFERER', request.get_full_path()
    )
    first_name = request.session.get('first_name', '')
    last_name = request.session.get('last_name', '')
    email_address = request.session.get('email_address', '')
    data_privacy_accepted = request.session.get('data_privacy_accepted', False)

    form = ContactForm(initial={
        'first_name': first_name, 'last_name': last_name,
        'email_address': email_address,
        'data_privacy_accepted': data_privacy_accepted,
        'subject': 'Website Enquiry'
    })

    return render(
        request, template_name, {'section': 'about', 'form': form}
    )


def session_types(request):
    return render(
        request, 'website/session_types.html', {'section': 'about', "session_types": SessionType.objects.filter(display_on_site=True)}
    )


def venues(request):
    locations_in_order = Venue.distinct_locations_in_order()
    locations = {}
    for location_name in locations_in_order:
        location = Location.objects.get(name=location_name)
        if location.venues.filter(display_on_site=True):
            locations[location] = location.venues.filter(display_on_site=True)

    return render(
        request, 'website/venues.html', {'section': 'about', "locations": locations}
    )