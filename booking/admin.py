# -*- coding: utf-8 -*-

from datetime import timedelta

from django.contrib import admin
from django.contrib.auth.models import User
from django.utils import timezone


from django_object_actions import DjangoObjectActions, takes_instance_or_queryset

from booking.models import Booking, WaitingListUser, Workshop, RegularClass, Register
from booking.forms import EventForm
from booking.email_helpers import send_email


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
            return queryset.filter(date__gte=timezone.now() - timedelta(hours=1))
        return queryset


class BookingInline(admin.TabularInline):
    fields = ('event', 'user', 'paid', 'status', 'no_show', 'attended')
    model = Booking
    can_delete = False
    extra = 0
    autocomplete_fields = ('user',)

    def get_queryset(self, request):
        return super(BookingInline, self).get_queryset(request).order_by('-status', 'no_show')

    def get_formset(self, request, obj=None, **kwargs):
        """
        Override the formset function in order to remove the add and change buttons beside the foreign key pull-down
        menus in the inline.
        """
        formset = super(BookingInline, self).get_formset(request, obj, **kwargs)
        form = formset.form
        widget = form.base_fields['user'].widget
        widget.can_add_related = False
        widget.can_change_related = False
        return formset


class WaitingListInline(admin.TabularInline):
    fields = ('user', 'date_joined')
    model = WaitingListUser
    can_delete = True
    can_add = False
    extra = 0
    max_num = 0
    autocomplete_fields = ('user',)
    readonly_fields = ('user', 'date_joined')


class EventAdmin(DjangoObjectActions, admin.ModelAdmin):
    list_display = (
        'name', 'get_date', 'venue', 'show_on_site', 'max_participants', 'get_spaces_left',
        'status', 'waiting_list'
    )

    list_filter = ('name', 'venue', EventDateListFilter)
    list_editable = ('show_on_site',)
    readonly_fields = ('cancelled',)
    actions_on_top = True
    ordering = ('date',)
    form = EventForm
    actions = ['cancel_event']
    change_actions = ['cancel_event']
    inlines = [BookingInline, WaitingListInline]

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
        ('Status', {
            'fields': ('cancelled',)
        }),
    ]

    def has_delete_permission(self, request, obj=None):
        return False

    def get_form(self, request, obj=None, **kwargs):
        """
        Override the formset function in order to remove the delete button beside the foreign key for venue
        """
        form = super().get_form(request, obj, **kwargs)
        widget = form.base_fields['venue'].widget
        widget.can_delete_related = False
        return form

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

    def get_spaces_left(self, obj):
        return obj.spaces_left
    get_spaces_left.short_description = 'Spaces left'

    def get_date(self, obj):
        return obj.date.strftime('%a %d %b %Y %H:%M (%Z)')
    get_date.short_description = 'Date'
    get_date.admin_order_field = 'date'

    def status(self, obj):
        if obj.cancelled:
            return 'CANCELLED'
        return 'OPEN'

    def waiting_list(self, obj):
        return obj.waitinglistusers.exists()
    waiting_list.boolean = True


    @takes_instance_or_queryset
    def cancel_event(self, request, queryset):
        for obj in queryset:
            event_type = 'class' if obj.event_type == 'regular_session' else 'workshop'

            if not obj.bookings.exists():
                obj.delete()
                self.message_user(request, '%s %s deleted (no open/cancelled bookings)' % (event_type.title(), obj))
            else:
                if obj.date <= timezone.now():
                    self.message_user(request, "Can't cancel past %s" % event_type)
                else:
                    obj.cancelled = True
                    obj.save()

                    open_bookings = obj.bookings.filter(status='OPEN', no_show=False)
                    open_bookings_count = open_bookings.count()
                    users_to_email = []
                    for booking in open_bookings:
                        users_to_email.append(booking.user.email)
                        if booking.status == 'OPEN' and not booking.no_show:
                            booking.status = 'CANCELLED'
                            booking.save()

                    if open_bookings:
                        send_email(
                            request,
                            subject='{} has been cancelled'.format(obj),
                            ctx={'event_type': event_type, 'event': obj},
                            template_txt='booking/email/event_cancelled.txt',
                            bcc_list=users_to_email
                        )

                    if open_bookings_count == 0:
                        msg = 'no open bookings'
                    else:
                        msg = 'users for {} open booking(s) have been emailed notification'.format(open_bookings_count)
                    self.message_user(request, '%s %s cancelled; %s' % (event_type.title(), obj,  msg))


class WorkshopAdmin(EventAdmin):

    def get_queryset(self, request):
        return super().get_queryset(request).filter(event_type='workshop')

    def status(self, obj):
        return super().status(obj)
    status.short_description = 'Workshop Status'

    @takes_instance_or_queryset
    def cancel_event(self, request, queryset):
        return super().cancel_event(request, queryset)
    cancel_event.short_description = 'Cancel workshop; this will cancel all bookings and email notifications to students.'
    cancel_event.label = 'Cancel workshop'
    cancel_event.attrs = {'style': 'font-weight: bold; color: red;'}


class RegularClassAdmin(EventAdmin):

    readonly_fields = ('cancelled', 'paypal_email')

    def get_form(self, request, obj=None, **kwargs):
        form = super(RegularClassAdmin, self).get_form(request, obj, **kwargs)
        form.base_fields['cost'].help_text = '(non-membership cost)'
        return form

    def get_queryset(self, request):
        return super().get_queryset(request).filter(event_type='regular_session')

    def status(self, obj):
        return super().status(obj)
    status.short_description = 'Class Status'

    @takes_instance_or_queryset
    def cancel_event(self, request, queryset):
        return super().cancel_event(request, queryset)
    cancel_event.short_description = 'Cancel class; this will cancel all bookings and email notifications to students.'
    cancel_event.label = 'Cancel class'
    cancel_event.attrs = {'style': 'font-weight: bold; color: red;'}


class RegisterAdmin(admin.ModelAdmin):
    list_filter = ('name', 'venue', EventDateListFilter)
    list_display = (
        'name', 'get_date', 'venue', 'get_spaces_left', 'waiting_list'
    )
    fields = ('name', 'get_date', 'venue')
    readonly_fields = ('name', 'get_date', 'venue')
    inlines = (BookingInline, WaitingListInline)
    ordering = ('date',)

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

    def get_queryset(self, request):
        return super().get_queryset(request).filter(cancelled=False)

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_spaces_left(self, obj):
        return obj.spaces_left
    get_spaces_left.short_description = 'Spaces left'

    def waiting_list(self, obj):
        return obj.waitinglistusers.exists()
    waiting_list.boolean = True

    def get_date(self, obj):
        return obj.date.strftime('%a %d %b %Y %H:%M (%Z)')
    get_date.short_description = 'Date'
    get_date.admin_order_field = 'date'


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
admin.site.register(Register, RegisterAdmin)
admin.site.register(WaitingListUser, WaitingListUserAdmin)
