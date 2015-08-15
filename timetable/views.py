from django.shortcuts import render, HttpResponse, get_object_or_404
from timetable.models import Instructor, TimetableSession, SessionType
import datetime


