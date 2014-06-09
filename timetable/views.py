from django.shortcuts import render, HttpResponse, get_object_or_404
from timetable.models import Instructor, Session, SessionType
import datetime


def index(request):

    today = datetime.datetime.today()
    timetable_items = Session.objects.filter(session_date__gte=today).order_by('session_date')
    session_types = SessionType.objects.all().order_by('name')
    return render(request, 'timetable/index.html', {'timetable_items': timetable_items, 'session_types': session_types})


def instructors(request):
    instructors = Instructor.objects.all().order_by('name')

    return render(request, 'timetable/instructors.html', {'instructors': instructors})


def instructor_info(request, instructor_id):
    instructor = get_object_or_404(Instructor, pk=instructor_id)
    return render(request, 'timetable/instructor.html', {'instructor': instructor})


def session_type_info(request, session_type_id):
    session_type_info = get_object_or_404(SessionType, pk=session_type_id)
    return render(request, 'timetable/session_type_info.html', {'session_type_info': session_type_info})


def filtered_session_type(request, session_type_id):
    today = datetime.datetime.today()
    session_type = get_object_or_404(SessionType, pk=session_type_id)
    timetable_items = Session.objects.filter(session_type_id=session_type.id, session_date__gte=today).order_by('session_date')
    return render(request, 'timetable/index.html', {'timetable_items': timetable_items})
