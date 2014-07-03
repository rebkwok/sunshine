from django.shortcuts import render, HttpResponse, get_object_or_404
from timetable.models import Instructor, Session, SessionType, Event
from gallery.models import Category, Image
from polefit.website.models import AboutInfo, PastEvent, Achievement
from django.utils import timezone
import datetime



def index(request):
    session_types = SessionType.objects.filter(regular_session=True).order_by('name')
    return render(request, 'website/index.html', {'session_types': session_types})

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


def classes(request, session_type_id):
    session_types = SessionType.objects.filter(regular_session=True).order_by('name')
    selected_session = get_object_or_404(SessionType, pk=session_type_id)
    return render(request, 'website/classes.html', {'selected_session': selected_session,
                                                    'session_types': session_types,
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
def instructor_info(request, instructor_id):
    session_types = SessionType.objects.filter(regular_session=True).order_by('name')
    instructor = get_object_or_404(Instructor, pk=instructor_id)
    return render(request, 'website/instructors.html', {'section': 'instructors', 'instructor': instructor,
                                                        'session_types': session_types,})

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
    now = timezone.now()
    session_types = SessionType.objects.filter(regular_session=True).order_by('name')
    tt_session_types = SessionType.objects.filter(session__session_type__isnull=False, session__session_date__gte=now).distinct().order_by('name')
    timetable_items = Session.objects.filter(session_date__gte=now).order_by('session_date')
    return render(request, 'website/timetable.html', {'timetable_items': timetable_items,
                                                    'session_types': session_types,
                                                    'tt_session_types':tt_session_types,
                                                    'section': 'timetable',
                                                     'sidebar_section':'all'})


def weekly_table(request, week):
    now = timezone.now()
    if week == 'this':
        sidebar_section = 'this_week'
        offset = 0
    elif week == 'next':
        sidebar_section = 'next_week'
        offset = 7

    start = now.replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=(0 - now.weekday() + offset))
    end = start + datetime.timedelta(days=7)

    session_types = SessionType.objects.filter(regular_session=True).order_by('name')
    tt_session_types = SessionType.objects.filter(session__session_type__isnull=False, session__session_date__gte=start).distinct().order_by('name')

    session_week = Session.objects.filter(session_date__range=[start, end]).order_by('session_date')
    mon_sessions = [session for session in session_week if session.get_weekday() == 'Mon']
    tues_sessions = [session for session in session_week if session.get_weekday() == 'Tues']
    wed_sessions = [session for session in session_week if session.get_weekday() == 'Wed']
    thurs_sessions = [session for session in session_week if session.get_weekday() == 'Thurs']
    fri_sessions = [session for session in session_week if session.get_weekday() == 'Fri']
    sat_sessions = [session for session in session_week if session.get_weekday() == 'Sat']
    sun_sessions = [session for session in session_week if session.get_weekday() == 'Sun']
    sessions = [mon_sessions, tues_sessions, wed_sessions, thurs_sessions, fri_sessions, sat_sessions, sun_sessions]
    return render(request, 'website/weekly_table.html', {'sessions': sessions,
                                                         'start': start,
                                                         'session_types': session_types,
                                                         'tt_session_types': tt_session_types,
                                                         'section': 'timetable',
                                                         'sidebar_section':sidebar_section})

def sessions_by_type(request, session_type_id):
    session_types = SessionType.objects.filter(regular_session=True).order_by('name')
    today = timezone.now()
    session_type = get_object_or_404(SessionType, pk=session_type_id)
    timetable_items = Session.objects.filter(session_type_id=session_type.id, session_date__gte=today).order_by('session_date')
    return render(request, 'website/timetable.html', {'timetable_items': timetable_items,
                                                    'session_types': session_types,
                                                    'section': 'timetable',
                                                    'sidebar_section':session_type.id})

