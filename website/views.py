from django.urls import reverse
from django.conf import settings
from django.shortcuts import render, get_object_or_404, \
    HttpResponseRedirect
from django.contrib import messages
from django.utils.safestring import mark_safe

from booking.email_helpers import send_email
from timetable.models import Instructor, TimetableSession, SessionType
from website.models import AboutInfo, PastEvent, Achievement
from website.forms import BookingRequestForm, ContactForm


def about(request):
    about_text = AboutInfo.objects.all()
    events = PastEvent.objects.all().order_by('-id')
    achievements = Achievement.objects.filter(display=True)
    return render(request, 'website/about.html', {'section': 'about',
                                                  'about_text': about_text,
                                                  'events': events,
                                                  'achievements': achievements})


def classes(request):
    session_types = SessionType.objects.filter(regular_session=True).order_by('index')
    return render(
        request, 'website/classes.html',
        {'section': 'classes', 'session_types': session_types}
    )


def parties(request):
    return render(request, 'website/parties.html', {'section': 'parties'})


def membership(request):
    return render(request, 'website/membership.html', {'section': 'membership'})


def instructors(request):
    instructor_list = Instructor.objects.all().order_by('index')
    return render(
        request, 'website/instructors.html',
        {
            'section': 'instructors', 'instructors': instructor_list
        }
    )


def venues(request):
    return render(request, 'website/venues.html', {'section': 'venues'})


def booking_request(
        request, session_pk, template_name='website/booking_request.html'
):

    tt_session = get_object_or_404(TimetableSession, id=session_pk)

    if request.method == 'POST':

        form = BookingRequestForm(request.POST, session=tt_session)

        if form.is_valid():
            email_address = form.cleaned_data['email_address']
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            cc = form.cleaned_data['cc']
            date_booked = form.cleaned_data['date']
            ctx = {
                    'session': tt_session,
                    'first_name': first_name,
                    'last_name': last_name,
                    'email_address': email_address,
                    'date_booked': date_booked,
                    'additional_msg': form.cleaned_data['additional_message'],
                }

            emailed = send_email(
                request, 'Booking request for {}'.format(tt_session), ctx,
                'website/email/booking_request_email.txt',
                template_html='website/email/booking_request_email.html',
                to_list=[settings.DEFAULT_STUDIO_EMAIL],
                cc_list=[email_address] if cc else [],
                reply_to_list=[email_address]
            )
            if emailed == 'OK':
                messages.info(
                    request,
                    "Your booking request for {} ({}) has been sent and we will "
                    "confirm your booking by email as soon as possible!".format(
                        tt_session, date_booked
                    )
                )
            else:
                messages.error(
                    request, "A problem occurred while submitting your"
                             " request.  Tech support has been notified."
                )

            request.session['first_name'] = first_name
            request.session['last_name'] = last_name
            request.session['email_address'] = email_address
            # required field, so must be True if form valid
            request.session['data_privacy_accepted'] = True

            return HttpResponseRedirect(reverse('timetable:timetable'))

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

    else:
        first_name = request.session.get('first_name', '')
        last_name = request.session.get('last_name', '')
        email_address = request.session.get('email_address', '')
        data_privacy_accepted = request.session.get('data_privacy_accepted', False)

        form = BookingRequestForm(initial={
            'first_name': first_name, 'last_name': last_name,
            'email_address': email_address,
            'data_privacy_accepted': data_privacy_accepted
        }, session=tt_session)

    return render(
        request, template_name,
        {'section': 'contact', 'form': form, 'session': tt_session},
    )


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

        emailed = send_email(
            request, subject, ctx,
            'website/email/contact_form_email.txt',
            template_html='website/email/contact_form_email.html',
            to_list=[settings.DEFAULT_STUDIO_EMAIL],
            cc_list=[email_address] if cc else [],
            reply_to_list=[email_address]
        )
        if emailed == 'OK':
            messages.info(
                request,
                "Thank you for your enquiry! Your email has been sent and "
                "we'll get back to you as soon as possible."
            )
        else:
            messages.error(
                request, "A problem occurred while submitting your"
                         " request.  Tech support has been notified."
            )

        request.session['first_name'] = first_name
        request.session['last_name'] = last_name
        request.session['email_address'] = email_address
        # required field, so must be True if form valid
        request.session['data_privacy_accepted'] = True

        return_url = request.session.get(
            'return_url', reverse('website:contact')
        )
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
            request, template_name, {'section': 'contact', 'form': form}
        )


def get_initial_contact_form(request):
    request.session['return_url'] = request.META.get(
        'HTTP_REFERER', request.get_full_path()
    )
    first_name = request.session.get('first_name', '')
    last_name = request.session.get('last_name', '')
    email_address = request.session.get('email_address', '')
    data_privacy_accepted = request.session.get('data_privacy_accepted', False)

    page = request.session['return_url'].split('/')[-2]

    subjects = {
        'membership': 'Membership Enquiry',
        'classes': 'Class Booking Enquiry',
        'parties': 'Party Booking'
    }

    return ContactForm(initial={
        'first_name': first_name, 'last_name': last_name,
        'email_address': email_address,
        'data_privacy_accepted': data_privacy_accepted,
        'subject': subjects.get(page, 'General Enquiry')
    })


def contact_form(request, template_name='website/contact_form.html'):
    if request.method == 'POST':
        return process_contact_form(request, template_name)

    form = get_initial_contact_form(request)

    return render(
        request, template_name, {'section': 'contact', 'form': form}
    )


def contact(request):
    return contact_form(request, template_name='website/contact_us.html')

