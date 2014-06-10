from django.shortcuts import render, HttpResponse, get_object_or_404
from timetable.models import Instructor, Session, SessionType
import datetime

session_types = SessionType.objects.all().order_by('name')

def index(request):
    return render(request, 'website/index.html', {'session_types': session_types})

def about(request):
    return render(request, 'website/about.html', {'section': 'about', 'session_types': session_types})

def classes_polefit(request):
    return render(request, 'website/classes_polefit.html', {'section': 'classes_polefit', 'dd_section': 'class_dd'})

def classes_hoop(request):
    return render(request, 'website/classes_hoop.html', {'section': 'classes_hoop', 'dd_section': 'class_dd'})

def classes_balletfit(request):
    return render(request, 'website/classes_balletfit.html', {'section': 'classes_balletfit', 'dd_section': 'class_dd'})

def classes_bouncefit(request):
    return render(request, 'website/classes_bouncefit.html', {'section': 'classes_bouncefit', 'dd_section': 'class_dd'})

def classes_stretch(request):
    return render(request, 'website/classes_stretch.html', {'section': 'classes_stretch', 'dd_section': 'class_dd'})

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

def venues(request):
    return render(request, 'website/venues.html', {'section': 'venues', 'session_types': session_types})

def gallery(request):
    return render(request, 'website/gallery.html', {'section': 'gallery', 'session_types': session_types})