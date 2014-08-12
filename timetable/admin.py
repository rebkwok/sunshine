import datetime
from django import forms
from django.http import HttpResponse
from django.template import RequestContext, loader
from django.shortcuts import render_to_response
from django.contrib import admin
from django.contrib.admin import DateFieldListFilter
from timetable.models import Instructor, Session, SessionType, Venue, Event, FixedSession
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.core.context_processors import csrf





class InstructorAdmin(admin.ModelAdmin):
    list_display = ('name', 'regular_instructor', 'has_photo')



class VenueAdmin(admin.ModelAdmin):
    list_display = ('venue', 'address', 'postcode')

class SessionTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'regular_session', 'has_photo')


class SessionDateListFilter(admin.SimpleListFilter):
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = _('session dates')

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'date'

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples. The first element in each
        tuple is the coded value for the option that will
        appear in the URL query. The second element is the
        human-readable name for the option that will appear
        in the right sidebar.
        """
        return (
            ('today', _('Today')),
            ('this_week', _('This week')),
            ('next_week', _('Next week')),
            ('this_month', _('This month')),
        )

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.
        """

        today = timezone.now()

        if self.value() == 'this_week':
            start = today.replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=(0 - today.weekday()))
            end = start + datetime.timedelta(days=7)
            return queryset.filter(session_date__range=[start, end])
        if self.value() == 'next_week':
            start = today.replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=(0 - today.weekday() + 7))
            end = start + datetime.timedelta(days=7)
            return queryset.filter(session_date__range=[start, end])
        if self.value() == 'today':
            return queryset.filter(session_date__year=today.year, session_date__month=today.month, session_date__day=today.day)
        if self.value() == 'this_month':
            return queryset.filter(session_date__year=today.year, session_date__month=today.month)


class SessionAdmin(admin.ModelAdmin):
    list_display = ('session_type', 'level', 'instructor', 'show_instructor', 'get_weekday', 'session_date', 'duration', 'venue',
                    'bookable', )
    fieldsets = [
        ('Session information', {'fields': ['session_type', 'level', 'instructor', 'show_instructor', 'venue', 'spaces']}),
        ('Date and time',        {'fields': ['session_date', 'duration']}),
         ]
    ordering = ['session_date']
    date_hierarchy = 'session_date'
    save_as = True
    actions = ['duplicate_event']
    list_filter = [SessionDateListFilter, 'session_type', 'instructor', 'venue']
    #change_list_template = "admin/change_list_filter_sidebar.html"
    #change_list_filter_template = "admin/filter_listing.html"


    class DuplicateSessionForm(forms.Form):
        _selected_action = forms.CharField(widget=forms.MultipleHiddenInput)


    def duplicate_event(self, request, queryset):

        """
        Action which duplicates the selected session objects for the same day/time in the following week.

        This action first displays a confirmation page whichs shows all the
        selected sessions to be duplicated, with a Confirm and Cancel button.

        Next, it duplicates all selected objects and redirects back to the change list. (Or ignores duplication and just
        redirects back to change list if Cancel is chosen.
        """
        form = None

        # The user has already confirmed the duplication.
        # Do the duplication and return a None to display the change list view again.
        if 'duplicate' in request.POST:
            form = self.DuplicateSessionForm(request.POST)

            for object in queryset:
                object.id = None
                object.session_date = object.session_date + datetime.timedelta(days=7)
                object.save()

            rows_updated = queryset.count()
            if rows_updated == 1:
                message_bit = "1 session was "
            else:
                message_bit = "%s sessions were" % rows_updated
            self.message_user(request, "%s successfully duplicated for the following week." % message_bit)
            return None

        elif 'cancel' in request.POST:
            return None

        if not form:
            form = self.DuplicateSessionForm(initial={'_selected_action': request.POST.getlist(admin.ACTION_CHECKBOX_NAME)})

        data = {'sessions': queryset, 'duplicate_form': form,}
        data.update(csrf(request))

        # Display the confirmation page
        return render_to_response('timetable/duplicate_session.html', data)

    duplicate_event.short_description = "Duplicate for next week"

class FixedSessionAdmin(admin.ModelAdmin):
    list_display = ('session_type', 'level', 'instructor', 'show_instructor', 'session_day', 'session_time', 'duration', 'venue',
                    'bookable', )
    fieldsets = [
        ('Session information', {'fields': ['session_type', 'level', 'instructor', 'show_instructor', 'venue', 'spaces']}),
        ('Date and time',        {'fields': ['session_day', 'session_time', 'duration']}),
         ]
    ordering = ['session_day']

    list_filter = ['session_type', 'instructor', 'venue']
    #change_list_template = "admin/change_list_filter_sidebar.html"
    #change_list_filter_template = "admin/filter_listing.html"


class EventAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_event_weekday', 'event_date', 'end_time')

admin.site.register(Instructor, InstructorAdmin)
admin.site.register(Session, SessionAdmin)
admin.site.register(FixedSession, FixedSessionAdmin)
admin.site.register(SessionType, SessionTypeAdmin)
admin.site.register(Event, EventAdmin)
admin.site.register(Venue, VenueAdmin)

