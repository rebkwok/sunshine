import datetime

from django.core.urlresolvers import reverse
from django.conf import settings
from django.shortcuts import render, HttpResponse, get_object_or_404, \
    HttpResponseRedirect
from django.utils import timezone
from django.views.generic import ListView
from django.core.mail.message import EmailMessage, EmailMultiAlternatives
from django.template.loader import get_template
from django.template import Context
from django.contrib import messages
from django.utils.safestring import mark_safe
from django.core.mail import send_mail

from timetable.models import Instructor, TimetableSession, SessionType, Venue
from gallery.models import Category, Image
from website.models import AboutInfo, PastEvent, Achievement
from website.forms import TimetableFilter, BookingRequestForm, ContactForm


def about(request):
    about_text = AboutInfo.objects.all()
    events = PastEvent.objects.all().order_by('-id')
    achievements = Achievement.objects.filter(display=True)
    return render(request, 'website/about.html', {'section': 'about',
                                                  'about_text': about_text,
                                                  'events' : events,
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


def gallery(request):
    categories = Category.objects.all().order_by('name')

    # import ipdb; ipdb.set_trace()
    category_choice = request.GET.getlist('category', ['All'])[0]
    if category_choice == 'All':
        images = Image.objects.all()
        cat_selection = 'All'
    else:
        images = Image.objects.filter(category__id=int(category_choice))
        cat_selection = int(category_choice)

    return render(request, 'website/gallery.html', {'section': 'gallery',
                                                    'cat_selection': cat_selection,
                                                    'categories': categories,
                                                    'images': images,
                                                    'total_image_count': Image.objects.all().count()
                                                    })


class TimetableListView(ListView):
    model = TimetableSession
    context_object_name = 'timetable_sessions'
    template_name = 'website/timetable.html'

    def get_queryset(self):

        queryset = TimetableSession.objects.all().order_by(
                'session_day', 'start_time', 'venue'
        )
        session_type = self.request.GET.get('filtered_session_type', 0)
        session_type = int(session_type)
        venue = self.request.GET.get('filtered_venue', '')

        if session_type != 0:
            queryset = queryset.filter(session_type__index=session_type)
        if venue != '':
            queryset = queryset.filter(venue__abbreviation=venue)

        return queryset

    def get_context_data(self, *args, **kwargs):
        # Call the base implementation first to get a context
        context = super(TimetableListView, self).get_context_data(**kwargs)
        context['section'] = 'timetable'
        context['venues'] = Venue.objects.all()

        session_type = self.request.GET.get('filtered_session_type', 0)
        session_type = int(session_type)
        venue = self.request.GET.get('filtered_venue', '')

        form = TimetableFilter(
            initial={'filtered_session_type': session_type, 'filtered_venue': venue}
        )

        context['form'] = form
        return context


def booking_request(request, session_pk, template_name='website/booking_request.html'):

    session = get_object_or_404(TimetableSession, id=session_pk)

    if request.method == 'POST':

        form = BookingRequestForm(request.POST, session=session)

        if form.is_valid():
            email_address = form.cleaned_data['email_address']
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            cc = form.cleaned_data['cc']
            date_booked = form.cleaned_data['date']
            ctx = Context(
                {
                    'session': session,
                    'host': 'http://{}'.format(request.META.get('HTTP_HOST')),
                    'first_name': first_name,
                    'last_name': last_name,
                    'email_address': email_address,
                    'date_booked': date_booked,
                    'additional_msg': form.cleaned_data['additional_message'],
                }
            )
            try:
                msg = EmailMultiAlternatives(
                    '{} Booking request for {}'.format(settings.ACCOUNT_EMAIL_SUBJECT_PREFIX, session),
                    get_template(
                        'website/email/booking_request_email.txt'
                    ).render(ctx),
                    settings.DEFAULT_FROM_EMAIL,
                    to=[settings.DEFAULT_STUDIO_EMAIL],
                    cc=[email_address] if cc else [],
                    reply_to=[email_address]
                )
                msg.attach_alternative(
                    get_template(
                        'website/email/booking_request_email.html'
                    ).render(ctx),
                    "text/html"
                )
                msg.send(fail_silently=False)

                messages.info(
                    request,
                    "Your booking request for {} ({}) has been sent and we will "
                    "confirm your booking by email as soon as possible!".format(
                        session, date_booked
                    )
                )
            except Exception as e:
                # send mail to tech support with Exception
                try:
                    send_mail('{} An error occurred! ({})'.format(
                            settings.ACCOUNT_EMAIL_SUBJECT_PREFIX,
                            'booking request'
                            ),
                        'An error occurred in {}\n\nThe exception '
                        'raised was "{}"\n\n'
                        'first_name: {}\n'
                        'last_name: {}\n'
                        'email: {}\n'
                        'booking: {} {}'.format(
                            __name__, repr(e), first_name, last_name,
                            email_address, session, date_booked
                        ),
                        settings.DEFAULT_FROM_EMAIL,
                        [settings.SUPPORT_EMAIL],
                        fail_silently=True)
                    messages.error(request, "A problem occurred while submitting "
                                        "your request.  Tech support has been notified.")
                except Exception:
                    messages.error(
                        request, mark_safe(
                            "A problem occurred while sending your request, "
                             "please contact the studio on "
                             "<a href='mailto:{}' target=_blank>{}</a> for "
                            "information".format(
                                settings.DEFAULT_STUDIO_EMAIL,
                                settings.DEFAULT_STUDIO_EMAIL
                            )
                        )
                    )
                    pass

            request.session['first_name'] = first_name
            request.session['last_name'] = last_name
            request.session['email_address'] = email_address

            return HttpResponseRedirect(reverse('website:timetable'))

        else:
            messages.error(
                request,
                mark_safe(
                    "There were errors in the following "
                    "fields: {}".format(form.errors)
                )
            )


    first_name = request.session.get('first_name', '')
    last_name = request.session.get('last_name', '')
    email_address = request.session.get('email_address', '')

    form = BookingRequestForm(session=session, initial={
        'first_name': first_name, 'last_name': last_name,
        'email_address': email_address
    })

    return render(
        request, template_name,
        {'section': 'contact', 'form': form, 'session': session},
    )


def process_contact_form(request):
    form = ContactForm(request.POST)

    if form.is_valid():
        subject = form.cleaned_data['subject']
        email_address = form.cleaned_data['email_address']
        first_name = form.cleaned_data['first_name']
        last_name = form.cleaned_data['last_name']
        cc = form.cleaned_data['cc']
        message = form.cleaned_data['message']

        ctx = Context(
            {
                'host': 'http://{}'.format(request.META.get('HTTP_HOST')),
                'first_name': first_name,
                'last_name': last_name,
                'email_address': email_address,
                'message': message,
            }
        )

        try:
            msg = EmailMultiAlternatives(
                '{} {}'.format(settings.ACCOUNT_EMAIL_SUBJECT_PREFIX, subject),
                get_template(
                    'website/email/contact_form_email.txt'
                ).render(ctx),
                settings.DEFAULT_FROM_EMAIL,
                to=[settings.DEFAULT_STUDIO_EMAIL],
                cc=[email_address] if cc else [],
                reply_to=[email_address]
            )
            msg.attach_alternative(
                get_template(
                    'website/email/contact_form_email.html'
                ).render(ctx),
                "text/html"
            )
            msg.send(fail_silently=False)

            messages.info(
                request,
                "Thank you for your enquiry! Your email has been sent and "
                "we'll get back to you as soon as possible."
            )
        except Exception as e:
            # send mail to tech support with Exception
            try:
                send_mail('{} An error occurred! ({})'.format(
                        settings.ACCOUNT_EMAIL_SUBJECT_PREFIX,
                        'contact form'
                        ),
                    'An error occurred in {}\n\nThe exception '
                    'raised was "{}"\n\n'
                    'first_name: {}\n'
                    'last_name: {}\n'
                    'email: {}\n'
                    'message: {}'.format(
                        __name__, repr(e), first_name, last_name,
                        email_address, message
                    ),
                    settings.DEFAULT_FROM_EMAIL,
                    [settings.SUPPORT_EMAIL],
                    fail_silently=True)
                messages.error(request, "A problem occurred while submitting "
                                        "the form.  Tech support has been notified.")
            except Exception as e:
                messages.error(
                    request, mark_safe(
                        "A problem occurred while submitting the form, "
                         "please contact the studio on "
                         "<a href='mailto:{}' target=_blank>{}</a> for "
                        "information".format(
                            settings.DEFAULT_STUDIO_EMAIL,
                            settings.DEFAULT_STUDIO_EMAIL
                        )
                    )
                )
                pass

        request.session['first_name'] = first_name
        request.session['last_name'] = last_name
        request.session['email_address'] = email_address

        return_url = request.session.get(
            'return_url', reverse('website:contact')
        )
        return HttpResponseRedirect(return_url)

    else:
        messages.error(
            request,
            mark_safe("There were errors in the following "
                      "fields: {}".format(form.errors)
                      )
        )


def get_initial_contact_form(request):
    request.session['return_url'] = request.META.get(
        'HTTP_REFERER', request.get_full_path()
    )
    first_name = request.session.get('first_name', '')
    last_name = request.session.get('last_name', '')
    email_address = request.session.get('email_address', '')

    page = request.session['return_url'].split('/')[-2]
    if page == 'membership':
        subject = 'Membership Enquiry'
    elif page == 'classes':
        subject = 'Class Booking Enquiry'
    elif page == 'parties':
        subject = 'Party Booking'
    else:
        subject = 'General Enquiry'

    return ContactForm(initial={
        'first_name': first_name, 'last_name': last_name,
        'email_address': email_address, 'subject': subject
    })

def contact_form(request, template_name='website/contact_form.html'):
    if request.method == 'POST':
        return process_contact_form(request)

    form = get_initial_contact_form(request)

    return render(
        request, template_name, {'section': 'contact', 'form': form}
    )


def contact(request, template_name='website/contact_us.html'):

    if request.method == 'POST':
        return process_contact_form(request)

    form = get_initial_contact_form(request)

    return render(
        request, template_name, {'section': 'contact', 'form': form}
    )


def admin_help_login(request):
    return render(
        request, 'website/admin_help/admin_help.html',
        {'section': 'none'}
    )


def admin_help_sessions(request):
    return render(
        request, 'website/admin_help/admin_help_sessions.html',
        {'section': 'none'}
    )


def admin_help_sessiontypes(request):
    return render(
        request, 'website/admin_help/admin_help_sessiontypes.html',
        {'section': 'none'}
    )


def admin_help_instructors(request):
    return render(
        request, 'website/admin_help/admin_help_instructors.html',
        {'section': 'none'}
    )


def admin_help_venues(request):
    return render(
        request, 'website/admin_help/admin_help_venues.html',
        {'section': 'none'}
    )


def admin_help_gallery(request):
    return render(
        request, 'website/admin_help/admin_help_gallery.html',
        {'section': 'none'}
    )


def admin_help_about(request):
    return render(
        request,
        'website/admin_help/admin_help_about.html',
        {'section': 'none'}
    )


def admin_help_events(request):
    return render(
        request,
        'website/admin_help/admin_help_events.html',
        {'section': 'none',}
    )