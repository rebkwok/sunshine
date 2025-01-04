from django.contrib import admin
from django.shortcuts import render, redirect
from django.urls import path, reverse
from django.utils.safestring import mark_safe

from .forms import UploadTimetableForm
from .models import Category, TimetableSession, SessionType, Venue
from .utils import upload_timetable


@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = ('name', 'addr', 'abbreviation', 'location', 'tab_order', 'image_img')

    fieldsets = (
        (
            "Venue",
            {"fields": ("name",)}
        ),
        (
            "Timetable details",
            {
                "fields": ("abbreviation", "location", "tab_order"),
                "description": "Details for displaying and ordering on timetable and booking pages"    
            },  
        ),
        (
            "Web page content",
            {
                "fields": ("address", "postcode", "description", "photo"),
                "description": "Details displayed on the Venues web page"    
            }
        ),
    )

    @mark_safe
    def image_img(self,obj):
        if obj.photo:
            return '<img src="%s"  height="60px"/>' % obj.photo.url
        else:
            return '-'
    image_img.short_description = "photo"

    def addr(self,obj):
        return f"{obj.address}, {obj.postcode}"
    addr.short_description = "address"


@admin.register(SessionType)
class SessionTypeAdmin(admin.ModelAdmin):
    list_display = ('order', 'name', 'image_img', 'display_on_site')
    fieldsets = (
        (
            "Session Type", 
            {
                'fields': ('name',),
                'description': (
                    'Every timetable session must have a session type.'
                    'Additional session types (not associated with timetabled classes) can be added here for inclusion on the "What we offer" page'
                )
            }
        ),
        (
            "Website content",
            {
                "fields": ("index", "description", "photo", "display_on_site"),
                "description": 'Details for the "What we offer" page'
            }
        )
    )

    @mark_safe
    def image_img(self,obj):
        if obj.photo:
            return '<img src="%s"  height="60px"/>' % obj.photo.url
        else:
            return '-'
    image_img.short_description = "photo"


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'colour'),
            'description': "Categories are used ONLY to (optionally) colour-code groups of classes on the timetable page"
        }),
    )


@admin.register(TimetableSession)
class TimetableSessionAdmin(admin.ModelAdmin):
    list_display = ('name', 'level', 'session_type', 'session_day',
                    'start_time', 'end_time', 'venue', 'max_participants', 'members_only', 'show_on_timetable_page')
    fieldsets = [
        ('Session name', {
            'fields': ['name', 'level'],
            'description': (
                'Classes generated from timetable sessions will be named with the session name and '
                'level (e.g. A session named "Pole dance" with level "All levels" will create classes '
                'named "Pole dance (All levels)".')
        }),
        ('Session categorisation', {
            'fields': ['session_type', 'category'],
            'description': (
                'Group classes for filtering and colour-coding on the timetable page; e.g. "Pole dance" and "Pole fitness" could both be assigned to a class type '
                '"Pole" (for filtering on the timetable), and to a category "Pole and aerial" for optional '
                'colour-coding on the timetable (class types and categories can be identical)')
        }),
        ('Session details', {
            'fields': ['venue', 'max_participants', 'cost',
                       'members_only', 'cancellation_fee', 'cancellation_period', 'show_on_timetable_page']
        }),
        ('Date and time', {
            'fields': ['session_day', 'start_time', 'end_time']
        }),
         ]
    ordering = ['session_day', 'start_time']

    list_filter = ['session_type', 'venue']
    list_editable = ('members_only', 'show_on_timetable_page')

    def get_urls(self):
        urls = super().get_urls()
        extra_urls = [
            path('upload/', self.upload_timetable, name="upload_timetable"),
        ]
        return extra_urls + urls

    def upload_timetable(self, request, template_name="timetable/upload_timetable_form.html"):

        if not request.user.is_superuser:
            return redirect(reverse("admin:index"))
        
        context = {
            'current_app': self.admin_site.name,
            'available_apps': self.admin_site.get_app_list(request),
            'site_header': "Sunshine Fitness"
        }

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
