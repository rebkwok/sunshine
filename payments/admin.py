from django.contrib import admin
from django.contrib.auth.models import User
from payments.models import PaypalBookingTransaction

from paypal.standard.ipn.models import PayPalIPN
from paypal.standard.ipn.admin import PayPalIPNAdmin


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
            return queryset.filter(entry__user__id=self.value())
        return queryset


class PaypalBookingTransactionAdmin(admin.ModelAdmin):

    list_display = ('id', 'get_user', 'invoice_id',
                    'transaction_id', 'get_booking_id')
    readonly_fields = ('id', 'get_user', 'invoice_id',
                       'get_booking_id')
    list_filter = (UserFilter,)
    list_select_related = ('booking',)

    def get_booking_id(self, obj):
        return obj.booking.id
    get_booking_id.short_description = "Booking id"

    def get_user(self, obj):
        return "{} {}".format(
            obj.entry.user.first_name, obj.entry.user.last_name
        )
    get_user.short_description = "User"


class PayPalAdmin(PayPalIPNAdmin):

    search_fields = [
        "txn_id", "recurring_payment_id", 'custom', 'invoice',
        'first_name', 'last_name'
    ]
    list_display = [
        "txn_id", "flag", "flag_info", "invoice", "custom",
        "payment_status", "buyer", "created_at"
    ]

    def buyer(self, obj):
        return "{} {}".format(obj.first_name, obj.last_name)
    buyer.admin_order_field = 'first_name'


admin.site.register(PaypalBookingTransaction, PaypalBookingTransactionAdmin)
admin.site.unregister(PayPalIPN)
admin.site.register(PayPalIPN, PayPalAdmin)
