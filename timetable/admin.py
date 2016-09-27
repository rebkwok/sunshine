from django.contrib import admin
from timetable.models import Instructor, TimetableSession, SessionType, Venue


class InstructorAdmin(admin.ModelAdmin):
    list_display = ('name', 'regular_instructor', 'has_photo')


class VenueAdmin(admin.ModelAdmin):
    list_display = ('venue', 'address', 'postcode')


class SessionTypeAdmin(admin.ModelAdmin):
    list_display = ('index', 'name', 'regular_session', 'has_photo')
    ordering = ['index',]


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


admin.site.register(Instructor, InstructorAdmin)
admin.site.register(TimetableSession, TimetableSessionAdmin)
admin.site.register(SessionType, SessionTypeAdmin)
admin.site.register(Venue, VenueAdmin)
