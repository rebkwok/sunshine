# -*- coding: utf-8 -*-
import pytz
from datetime import timedelta
from django.contrib import admin
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.safestring import mark_safe

from django_object_actions import DjangoObjectActions, takes_instance_or_queryset

from booking.models import (
    Booking, GiftVoucher, GiftVoucherType, ItemVoucher, Membership, MembershipType, TotalVoucher, 
    WaitingListUser, Workshop, RegularClass, Private, Event
)
from booking.forms import EventForm, ItemVoucherForm
from booking.email_helpers import send_email
from stripe_payments.utils import process_refund
from stripe_payments.models import StripeRefund


def format_date_in_local_timezone(utc_datetime):
    local_tz = pytz.timezone('Europe/London')
    local_datetime = utc_datetime.astimezone(local_tz)
    return local_datetime.strftime('%a %d %b %Y %H:%M (%Z)')


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


class DateListFilterMixin:

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

    def choices(self, cl):
        for lookup, title in self.lookup_choices:
            yield {
                'selected': self.value() == lookup,
                'query_string': cl.get_query_string({self.parameter_name: lookup,}, []),
                'display': title,
            }


class BookingDateListFilter(DateListFilterMixin, admin.SimpleListFilter):
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = 'event date'

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'event__date'

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
        if self.value() is None:
            return queryset.filter(event__date__gte=timezone.now())
        return queryset


class EventDateListFilter(DateListFilterMixin, admin.SimpleListFilter):
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = 'date'

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'date'

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
        'name', 'get_date', 'venue', 'show_on_site', 'members_only', 'max_participants', 'get_spaces_left',
        'status', 'waiting_list'
    )
    list_filter = ('name', 'venue', EventDateListFilter)

    list_editable = ('show_on_site', 'members_only')
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
                'description', 'members_only')
        }),
        ('Contacts', {
            'fields': ('contact_email', 'email_studio_when_booked')
        }),
        ('Payment Information', {
            'fields': ('cost',)
        }),
        ('Cancellation (refundable)', {
            'fields': ('allow_booking_cancellation', 'cancellation_period',
                       'cancellation_fee'),
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

    def get_spaces_left(self, obj):
        return obj.spaces_left
    get_spaces_left.short_description = 'Spaces left'

    def get_date(self, obj):
        return format_date_in_local_timezone(obj.date)
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
            event_names = dict(Event.EVENT_TYPES)
            event_type = 'class' if obj.event_type == 'regular_session' else event_names[obj.event_type]

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
                    for booking in open_bookings:
                        refunded = False
                        was_booked_with_membership = booking.membership is not None
                        if booking.status == 'OPEN' and not booking.no_show:
                            booking.status = 'CANCELLED'
                            if booking.membership:
                                booking.membership = None
                            elif booking.paid and booking.invoice:
                                # process refund
                                refunded = process_refund(request, booking)
                            booking.paid = False
                            booking.save()

                            send_email(
                                request,
                                subject='{} has been cancelled'.format(obj),
                                ctx={
                                    'event_type': event_type, 
                                    'event': obj, 
                                    'was_booked_with_membership': was_booked_with_membership,
                                    'refunded': refunded
                                },
                                template_txt='booking/email/event_cancelled.txt',
                                to_list=[booking.user.email]
                            )

                    if open_bookings_count == 0:
                        msg = 'no open bookings'
                    else:
                        msg = 'users for {} open booking(s) have been emailed notification'.format(open_bookings_count)
                    self.message_user(request, '%s %s cancelled; %s' % (event_type.title(), obj,  msg))


@admin.register(Workshop)
class WorkshopAdmin(EventAdmin):

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['event_type'].choices = [('workshop', "Workshop"),]
        return form

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.filter(event_type='workshop')

    def status(self, obj):
        return super().status(obj)
    status.short_description = 'Workshop Status'

    @takes_instance_or_queryset
    def cancel_event(self, request, queryset):
        return super().cancel_event(request, queryset)
    cancel_event.short_description = 'Cancel workshop; this will cancel all bookings and email notifications to students.'
    cancel_event.label = 'Cancel workshop'
    cancel_event.attrs = {'style': 'font-weight: bold; color: red;'}


@admin.register(RegularClass)
class RegularClassAdmin(EventAdmin):

    readonly_fields = ('cancelled',)
    actions = ['cancel_event', 'toggle_members_only']

    def get_form(self, request, obj=None, **kwargs):
        form = super(RegularClassAdmin, self).get_form(request, obj, **kwargs)
        form.base_fields['cost'].help_text = '(non-membership cost)'
        form.base_fields['event_type'].choices = [('regular_session', "Regular timetabled session"),]
        return form

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.filter(event_type='regular_session')

    def status(self, obj):
        return super().status(obj)
    status.short_description = 'Class Status'

    @takes_instance_or_queryset
    def cancel_event(self, request, queryset):
        return super().cancel_event(request, queryset)
    cancel_event.short_description = 'Cancel class; this will cancel all bookings and email notifications to students.'
    cancel_event.label = 'Cancel class'
    cancel_event.attrs = {'style': 'font-weight: bold; color: red;'}

    def toggle_members_only(self, request, queryset):
        for obj in queryset:
            obj.members_only = not obj.members_only
            obj.save()
    toggle_members_only.short_description = 'Toggle "members only" status.'
    

@admin.register(Private)
class PrivateAdmin(EventAdmin):

    readonly_fields = ('cancelled',)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['event_type'].choices = [('private', "Private lesson"),]
        return form

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.filter(event_type='private')

    def status(self, obj):
        return super().status(obj)
    status.short_description = 'Class Status'

    @takes_instance_or_queryset
    def cancel_event(self, request, queryset):
        return super().cancel_event(request, queryset)
    cancel_event.short_description = 'Cancel class; this will cancel all bookings and email notifications to students.'
    cancel_event.label = 'Cancel class'
    cancel_event.attrs = {'style': 'font-weight: bold; color: red;'}


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):

    exclude = ('booking_reference',)

    list_display = (
        'event_name', 'get_date', 'get_user', 'get_cost', 'paid', 'status',
        'no_show', 'refunded'
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

    def refunded(self, obj):
        return "Yes" if StripeRefund.objects.filter(booking_id=obj.id).exists() else "-"
    

@admin.register(WaitingListUser)
class WaitingListUserAdmin(admin.ModelAdmin):
    fields = ('user', 'event')
    list_display = ('user', 'event')
    list_filter = (UserFilter, 'event')
    search_fields = (
        'user__first_name', 'user__last_name', 'user__username', 'event__name'
    )


@admin.register(MembershipType)
class MembershipTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "cost", "active")
    list_editable = ('active',)


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    ...


@admin.register(ItemVoucher)
class ItemVoucherAdmin(admin.ModelAdmin):
    list_display = ('code', 'valid_for', 'start_date', 'expiry_date')
    # exclude gift voucher fields
    exclude = ('is_gift_voucher', 'activated', 'purchaser_email', 'name', 'message')
    
    fieldsets = (
      ('Voucher Properties', {
          'fields': ('code', 'discount', 'discount_amount')
      }),
      ('Valid dates', {
          'description': (
              "Start date defaults to the beginning of today; expiry date (if entered) "
              "will be automatically set to end of day on save."
            ),
          'fields': ('start_date', 'expiry_date')
      }),
      ('Limits on number of uses', {
          'description': (
              "Limit the times the voucher can be used; these are combined "
              "e.g. to make a voucher than can be used only once by one user, set both options to 1."
            ),
          'fields': ("max_vouchers", "max_per_user")
      }),
      ('Valid for:', {
          'fields': ("membership_types", "event_types")
      }),
   )

    form = ItemVoucherForm
    

    def valid_for(self, obj):
        return ", ".join(obj.valid_for())

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.filter(is_gift_voucher=False)


@admin.register(TotalVoucher)
class TotalVoucherAdmin(admin.ModelAdmin):

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.filter(is_gift_voucher=False)


@admin.register(GiftVoucherType)
class GiftVoucherTypeAdmin(admin.ModelAdmin):
    ...


@admin.register(GiftVoucher)
class GiftVoucherAdmin(admin.ModelAdmin):
    
    list_display = ("purchaser_email", "name", "paid", "activated", "link")
    exclude = ("slug", "item_voucher")
    fields = ("gift_voucher_type", "invoice", "paid")
    readonly_fields = ("invoice",)
    
    def activated(self, obj):
        return obj.voucher.activated
    
    def link(self, obj):
        return mark_safe(
            f'<a href="{obj.get_voucher_url()}">{obj.voucher.code}</a>'
        )
