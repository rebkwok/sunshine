from django.shortcuts import render, HttpResponse, get_object_or_404
from timetable.models import Instructor, TimetableSession, SessionType, Venue
from gallery.models import Category, Image
from website.models import AboutInfo, PastEvent, Achievement
from django.utils import timezone
import datetime


def about(request):
    session_types = SessionType.objects.filter(regular_session=True).order_by('name')
    about_text = AboutInfo.objects.all()
    events = PastEvent.objects.all().order_by('-id')
    achievements = Achievement.objects.filter(display=True)
    return render(request, 'website/about.html', {'section': 'about',
                                                  'session_types': session_types,
                                                  'about_text': about_text,
                                                  'events' : events,
                                                  'achievements': achievements})


def classes(request):
    session_types = SessionType.objects.filter(regular_session=True).order_by('index')
    return render(request, 'website/classes.html', {'session_types': session_types,
                                                    'dd_section': 'class_dd'})

def parties(request):
    session_types = SessionType.objects.filter(regular_session=True).order_by('name')
    return render(request, 'website/parties.html', {'section': 'parties', 'session_types': session_types,})

def booking(request):
    session_types = SessionType.objects.filter(regular_session=True).order_by('name')
    return render(request, 'website/booking.html', {'section': 'booking', 'session_types': session_types,})

def instructors(request):
    session_types = SessionType.objects.filter(regular_session=True).order_by('name')
    instructor_list = Instructor.objects.all().order_by('name')
    return render(request, 'website/instructors.html', {'section': 'instructors', 'instructors': instructor_list,
                                                        'session_types': session_types})

def events(request):
    session_types = SessionType.objects.filter(regular_session=True).order_by('name')
    recent = timezone.now() - datetime.timedelta(days=7)
    event_list = Event.objects.filter(event_date__gte=recent).order_by('event_date')
    return render(request, 'website/events.html', {'section': 'events', 'events': event_list,
                                                        'session_types': session_types})

def venues(request):
    session_types = SessionType.objects.filter(regular_session=True).order_by('name')
    return render(request, 'website/venues.html', {'section': 'venues', 'session_types': session_types})

def gallery(request):
    session_types = SessionType.objects.filter(regular_session=True).order_by('name')
    categories = Category.objects.all().order_by('name')
    images = Image.objects.all()
    return render(request, 'website/gallery.html', {'section': 'gallery',
                                                    'cat_selection': 'all',
                                                    'session_types': session_types,
                                                    'categories': categories,
                                                    'images': images})

def gallery_category(request, category_id):
    session_types = SessionType.objects.filter(regular_session=True).order_by('name')
    cat = get_object_or_404(Category, pk=category_id)
    categories = Category.objects.all().order_by('name')
    images = Image.objects.filter(category_id=cat.id)
    return render(request, 'website/gallery.html', {'images': images,
                                                    'categories': categories,
                                                    'session_types': session_types,
                                                    'section': 'gallery',
                                                    'cat': cat.id})


def timetable(request):


    session_types = SessionType.objects.filter(regular_session=True).order_by('name')

    venues = Venue.objects.all()
    timetable_sessions = TimetableSession.objects.all().order_by('venue', 'session_day', 'session_time')
    return render(request, 'website/timetable.html', {'timetable_sessions': timetable_sessions,
                                                         'session_types': session_types,
                                                         'section': 'timetable',
                                                         'venues': venues})

def admin_help_login(request):
    session_types = SessionType.objects.filter(regular_session=True).order_by('name')
    return render(request, 'website/admin_help/admin_help.html', {'section': 'none',
                                                    'session_types': session_types,
                                                    })

def admin_help_sessions(request):
    session_types = SessionType.objects.filter(regular_session=True).order_by('name')
    return render(request, 'website/admin_help/admin_help_sessions.html', {'section': 'none',
                                                    'session_types': session_types,
                                                    })

def admin_help_sessiontypes(request):
    session_types = SessionType.objects.filter(regular_session=True).order_by('name')
    return render(request, 'website/admin_help/admin_help_sessiontypes.html', {'section': 'none',
                                                    'session_types': session_types,
                                                    })

def admin_help_instructors(request):
    session_types = SessionType.objects.filter(regular_session=True).order_by('name')
    return render(request, 'website/admin_help/admin_help_instructors.html', {'section': 'none',
                                                    'session_types': session_types,
                                                    })

def admin_help_venues(request):
    session_types = SessionType.objects.filter(regular_session=True).order_by('name')
    return render(request, 'website/admin_help/admin_help_venues.html', {'section': 'none',
                                                    'session_types': session_types,
                                                    })

def admin_help_gallery(request):
    session_types = SessionType.objects.filter(regular_session=True).order_by('name')
    return render(request, 'website/admin_help/admin_help_gallery.html', {'section': 'none',
                                                    'session_types': session_types,
                                                    })

def admin_help_about(request):
    session_types = SessionType.objects.filter(regular_session=True).order_by('name')
    return render(request, 'website/admin_help/admin_help_about.html', {'section': 'none',
                                                    'session_types': session_types,
                                                    })

def admin_help_events(request):
    session_types = SessionType.objects.filter(regular_session=True).order_by('name')
    return render(request, 'website/admin_help/admin_help_events.html', {'section': 'none',
                                                    'session_types': session_types,
                                                    })
