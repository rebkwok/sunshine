import datetime

from django.contrib import admin

from timetable.models import Instructor, Session, SessionType, Venue, Event



def duplicate_event(modeladmin, request, queryset):
    for object in queryset:
        object.id = None
        object.session_date = object.session_date + datetime.timedelta(days=7)
        object.save()
duplicate_event.short_description = "Duplicate for next week"


class InstructorAdmin(admin.ModelAdmin):
    list_display = ('name', 'regular_instructor')

class SessionTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'regular_session')

class SessionAdmin(admin.ModelAdmin):
    list_display = ('session_type', 'level', 'instructor', 'get_weekday', 'session_date', 'duration', 'venue',
                    'bookable')
    fieldsets = [
        ('Session information', {'fields': ['session_type', 'level', 'instructor', 'venue', 'spaces']}),
        ('Date and time',        {'fields': ['session_date', 'duration']}),
         ]
    ordering = ['session_date']
    date_hierarchy = 'session_date'
    save_as = True
    actions = [duplicate_event]
    list_filter = ['session_type', 'instructor', 'venue']

class EventAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_event_weekday', 'event_date', 'end_time')

admin.site.register(Instructor, InstructorAdmin)
admin.site.register(Session, SessionAdmin)
admin.site.register(SessionType, SessionTypeAdmin)
admin.site.register(Event, EventAdmin)
admin.site.register(Venue)

