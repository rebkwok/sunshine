from django.shortcuts import render, HttpResponse, get_object_or_404
from timetable.models import Instructor, Session, SessionType, Event
from django.utils import timezone
import datetime

session_types = SessionType.objects.all().order_by('name')

def index(request):
    return render(request, 'website/index.html', {'session_types': session_types})

def about(request):
    return render(request, 'website/about.html', {'section': 'about', 'session_types': session_types})


def classes(request, session_type_id):
    selected_session = get_object_or_404(SessionType, pk=session_type_id)
    return render(request, 'website/classes.html', {'selected_session': selected_session,
                                                    'session_types': session_types,
                                                    'dd_section': 'class_dd'})

def booking(request):
    return render(request, 'website/booking.html', {'section': 'booking', 'session_types': session_types,})

def instructors(request):
    instructor_list = Instructor.objects.all().order_by('name')
    return render(request, 'website/instructors.html', {'section': 'instructors', 'instructors': instructor_list,
                                                        'session_types': session_types})
def instructor_info(request, instructor_id):
    instructor = get_object_or_404(Instructor, pk=instructor_id)
    return render(request, 'website/instructors.html', {'section': 'instructors', 'instructor': instructor,
                                                        'session_types': session_types,})

def events(request):
    recent = timezone.now() - datetime.timedelta(days=7)
    event_list = Event.objects.filter(event_date__gte=recent).order_by('event_date')
    return render(request, 'website/events.html', {'section': 'events', 'events': event_list,
                                                        'session_types': session_types})

def venues(request):
    return render(request, 'website/venues.html', {'section': 'venues', 'session_types': session_types})

def gallery(request):
    return render(request, 'website/gallery.html', {'section': 'gallery', 'session_types': session_types})

def timetable(request):
    now = datetime.datetime.today()
    timetable_items = Session.objects.filter(session_date__gte=now).order_by('session_date')
    return render(request, 'website/timetable.html', {'timetable_items': timetable_items,
                                                    'session_types': session_types,
                                                    'section': 'timetable'})

def sessions_by_type(request, session_type_id):
    today = datetime.datetime.today()
    session_type = get_object_or_404(SessionType, pk=session_type_id)
    timetable_items = Session.objects.filter(session_type_id=session_type.id, session_date__gte=today).order_by('session_date')
    return render(request, 'website/timetable.html', {'timetable_items': timetable_items,
                                                    'session_types': session_types,
                                                    'section': 'timetable'})