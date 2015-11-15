import datetime
from django import forms
from django.http import HttpResponse
from django.template import RequestContext, loader
from django.shortcuts import render_to_response
from django.contrib import admin
from django.contrib.admin import DateFieldListFilter
from timetable.models import Instructor, TimetableSession, SessionType, Venue
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.core.context_processors import csrf


class InstructorAdmin(admin.ModelAdmin):
    list_display = ('name', 'regular_instructor', 'has_photo')

class VenueAdmin(admin.ModelAdmin):
    list_display = ('venue', 'address', 'postcode')

class SessionTypeAdmin(admin.ModelAdmin):
    list_display = ('index', 'name', 'regular_session', 'has_photo')


class TimetableSessionAdmin(admin.ModelAdmin):
    list_display = ('name', 'session_type', 'level', 'session_day',
                    'start_time', 'end_time', 'venue',)
    fieldsets = [
        ('Session information', {
            'fields': ['name', 'session_type', 'level', 'membership_level',
                       'instructor', 'venue', 'cost', 'alt_cost']
        }),
        ('Date and time', {
            'fields': ['session_day', 'start_time', 'end_time']
        }),
         ]
    ordering = ['session_day', 'start_time']

    list_filter = ['session_type', 'instructor', 'venue']
    #change_list_template = "admin/change_list_filter_sidebar.html"
    #change_list_filter_template = "admin/filter_listing.html"


admin.site.register(Instructor, InstructorAdmin)
admin.site.register(TimetableSession, TimetableSessionAdmin)
admin.site.register(SessionType, SessionTypeAdmin)
admin.site.register(Venue, VenueAdmin)
