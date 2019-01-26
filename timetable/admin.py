from django.contrib import admin

from timetable.models import Instructor, TimetableSession, SessionType, Venue


class InstructorAdmin(admin.ModelAdmin):
    list_display = ('name', 'regular_instructor', 'has_photo')

    def has_photo(self, obj):
        return bool(obj.photo)
    has_photo.short_description = 'Photo uploaded'
    has_photo.boolean = True


class VenueAdmin(admin.ModelAdmin):
    list_display = ('venue', 'address', 'postcode')


class SessionTypeAdmin(admin.ModelAdmin):
    list_display = ('index', 'name', 'regular_session', 'has_photo')
    ordering = ['index',]

    def has_photo(self, obj):
        return bool(obj.photo)
    has_photo.short_description = 'Photo uploaded'
    has_photo.boolean = True


class TimetableSessionAdmin(admin.ModelAdmin):
    list_display = ('name', 'session_type', 'level', 'session_day',
                    'start_time', 'end_time', 'venue', 'max_participants')
    fieldsets = [
        ('Session information', {
            'fields': ['name', 'session_type', 'level', 'membership_category',
                       'instructor', 'venue', 'max_participants', 'cost', 'alt_cost']
        }),
        ('Date and time', {
            'fields': ['session_day', 'start_time', 'end_time']
        }),
         ]
    ordering = ['session_day', 'start_time']

    list_filter = ['session_type', 'instructor', 'venue']

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        membership = form.base_fields['membership_category']
        membership.choices.insert(0, (None, '------'))
        return form


admin.site.register(Instructor, InstructorAdmin)
admin.site.register(TimetableSession, TimetableSessionAdmin)
admin.site.register(SessionType, SessionTypeAdmin)
admin.site.register(Venue, VenueAdmin)
