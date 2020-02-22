from django.contrib import admin
from django.shortcuts import render
from django.urls import path

from timetable.forms import UploadTimetableForm
from timetable.models import Instructor, TimetableSession, SessionType, Venue
from timetable.utils import upload_timetable


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

    def get_urls(self):
        urls = super().get_urls()
        extra_urls = [
            path('upload/', self.upload_timetable, name="upload_timetable"),
        ]
        return extra_urls + urls

    def upload_timetable(self, request, template_name="timetable/upload_timetable_form.html"):

        context = {'current_app': self.admin_site.name, 'available_apps': self.admin_site.get_app_list(request)}

        if request.method == 'POST':
            form = UploadTimetableForm(request.POST)
            if form.is_valid():
                start_date = form.cleaned_data['start_date']
                end_date = form.cleaned_data['end_date']
                session_ids = form.cleaned_data['sessions']
                show_on_site = form.cleaned_data['show_on_site']

                created_classes, existing_classes, duplicate_classes = upload_timetable(
                    start_date, end_date, session_ids, show_on_site, request.user
                )
                context.update({'start_date': start_date,
                           'end_date': end_date,
                           'created_classes': created_classes,
                           'existing_classes': existing_classes,
                           'duplicate_classes': duplicate_classes,
                           'sidenav_selection': 'upload_timetable'})
                return render(
                    request, 'timetable/upload_timetable_confirmation.html',
                    context
                )
        else:
            form = UploadTimetableForm()
            context.update({'form': form})
        return render(request, template_name, context)

admin.site.register(Instructor, InstructorAdmin)
admin.site.register(TimetableSession, TimetableSessionAdmin)
admin.site.register(SessionType, SessionTypeAdmin)
admin.site.register(Venue, VenueAdmin)
