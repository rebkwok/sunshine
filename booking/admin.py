# -*- coding: utf-8 -*-
from django.contrib import admin
from django.contrib.auth.models import User
from django.utils import timezone

from booking.models import Event, Booking, WaitingListUser, Workshop, RegularClass
from booking.forms import BookingInlineFormset, EventForm, UserModelChoiceField


class UserFilter(admin.SimpleListFilter):

    title = 'User'
    parameter_name = 'user'

    def lookups(self, request, model_admin):
        qs = User.objects.all().order_by('first_name')
        return [
            (
                user.id,
                "{} {} ({})".format(
                    user.first_name, user.last_name, user.username
                )
             ) for user in qs
            ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(user__id=self.value())
        return queryset


class BookingDateListFilter(admin.SimpleListFilter):
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = 'date'

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'event__date'

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples. The first element in each
        tuple is the coded value for the option that will
        appear in the URL query. The second element is the
        human-readable name for the option that will appear
        in the right sidebar.
        """
        return (
            ('past', ('past events only')),
            ('upcoming', ('upcoming events only')),
        )

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.
        """
        # Compare the requested value
        # to decide how to filter the queryset.
        if self.value() == 'past':
            return queryset.filter(event__date__lte=timezone.now())
        if self.value() == 'upcoming':
            return queryset.filter(event__date__gte=timezone.now())
        return queryset


class EventDateListFilter(admin.SimpleListFilter):
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = 'date'

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
            (None, 'Upcoming events only'),
            ('past', 'Past events only'),
            ('all', 'All events'),
        )

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.
        """
        # Compare the requested value
        # to decide how to filter the queryset.
        if self.value() == 'past':
            return queryset.filter(date__lte=timezone.now())
        if self.value() is None:
            return queryset.filter(date__gte=timezone.now())
        return queryset


class BookingInline(admin.TabularInline):
    fields = ('event', 'user', 'paid', 'status', 'no_show', 'attended')
    model = Booking
    can_delete = False
    extra = 1

    formset = BookingInlineFormset

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "user":
            booked_user_ids = []
            parent_obj_id = request.resolver_match.args
            if parent_obj_id:
                event = Event.objects.get(id=parent_obj_id[0])
                booked_user_ids = [bk.user.id for bk in event.bookings.all()]
            return UserModelChoiceField(
                queryset=User.objects.exclude(id__in=booked_user_ids)
            )
        return super(
            BookingInline, self
        ).formfield_for_foreignkey(db_field, request, **kwargs)


class EventAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'date', 'venue', 'show_on_site', 'max_participants', 'get_spaces_left'
    )
    list_filter = (EventDateListFilter, 'name')
    list_editable = ('show_on_site',)
    inlines = (BookingInline,)
    actions_on_top = True
    ordering = ('date',)
    form = EventForm

    fieldsets = [
        ('Event/Workshop details', {
            'fields': (
                'name', 'date', 'venue', 'event_type', 'max_participants',
                'description')
        }),
        ('Contacts', {
            'fields': ('contact_email', 'email_studio_when_booked')
        }),
        ('Payment Information', {
            'fields': ('cost', 'paypal_email')
        }),
        ('Cancellation (refundable)', {
            'fields': ('allow_booking_cancellation', 'cancellation_period',),
        }),
        ('Display options', {
            'fields': ('show_on_site',)
        }),
    ]

    def get_spaces_left(self, obj):
        return obj.spaces_left
    get_spaces_left.short_description = '# Spaces left'


class WorkshopAdmin(EventAdmin):

    def get_queryset(self, request):
        return super(
            WorkshopAdmin, self
        ).get_queryset(request).filter(event_type='workshop')


class RegularClassAdmin(EventAdmin):

    def get_queryset(self, request):
        return super(
            RegularClassAdmin, self
        ).get_queryset(request).filter(event_type='regular_session')


class BookingAdmin(admin.ModelAdmin):

    exclude = ('booking_reference',)

    list_display = (
        'event_name', 'get_date', 'get_user', 'get_cost', 'paid', 'status',
        'no_show'
    )

    list_filter = (BookingDateListFilter, UserFilter, 'event')

    search_fields = (
        'user__first_name', 'user__last_name', 'user__username', 'event__name'
    )

    readonly_fields = ('booking_reference', 'date_booked', 'date_rebooked')

    actions_on_top = True
    actions_on_bottom = False

    def get_date(self, obj):
        return obj.event.date
    get_date.short_description = 'Date'
    get_date.admin_order_field = 'event__date'

    def event_name(self, obj):
        return obj.event.name
    event_name.short_description = 'Event/Workshop'
    event_name.admin_order_field = 'event'

    def get_user(self, obj):
        return '{} {} ({})'.format(
            obj.user.first_name, obj.user.last_name, obj.user.username
        )
    get_user.short_description = 'User'
    get_user.admin_order_field = 'user__first_name'

    actions = ['confirm_space']

    def get_cost(self, obj):
        return u"\u00A3{:.2f}".format(obj.event.cost)
    get_cost.short_description = 'Cost'


class WaitingListUserAdmin(admin.ModelAdmin):
    fields = ('user', 'event')
    list_display = ('user', 'event')
    list_filter = (UserFilter, 'event')
    search_fields = (
        'user__first_name', 'user__last_name', 'user__username', 'event__name'
    )


admin.site.register(RegularClass, RegularClassAdmin)
admin.site.register(Workshop, WorkshopAdmin)
admin.site.register(Booking, BookingAdmin)
admin.site.register(WaitingListUser, WaitingListUserAdmin)
