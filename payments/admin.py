import shortuuid

from django.contrib import admin
from django.contrib.auth.models import User
from payments.models import PaypalBookingTransaction
from django.template.response import TemplateResponse
from django.urls import path

from paypal.standard.ipn.models import PayPalIPN
from paypal.standard.ipn.admin import PayPalIPNAdmin

from booking.views.booking_views import get_paypal_dict
from payments.forms import PayPalPaymentsUpdateForm
from payments.views import ConfirmRefundView


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
            return queryset.filter(booking__user__id=self.value())
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
            obj.booking.user.first_name, obj.booking.user.last_name
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

    def get_urls(self):
        urls = super().get_urls()
        extra_urls = [
            path('test-paypal-email/', self.paypal_email_test_view, name="test_paypal_email"),
            path('confirm-refunded/<int:pk>', self.confirm_refund, name="confirm_refund"),
        ]
        return extra_urls + urls

    def paypal_email_test_view(self, request):
        ctx = {'current_app': self.admin_site.name, 'available_apps': self.admin_site.get_app_list(request)}
        if request.method == 'GET':
            email = request.GET.get('email', '')
            ctx.update({'email': email})
        elif request.method == 'POST':
            email = request.POST.get('email')
            if not email:
                ctx.update(
                    {'email_errors': 'Please enter an email address to test'}
                )
            else:
                ramdomnum = shortuuid.ShortUUID().random(length=6)
                invoice_id = '{}_{}'.format(email, ramdomnum)
                host = 'http://{}'.format(request.META.get('HTTP_HOST'))
                paypal_form = PayPalPaymentsUpdateForm(
                    initial=get_paypal_dict(
                        host,
                        0.01,
                        'paypal_test',
                        invoice_id,
                        'paypal_test 0 {} {} {}'.format(
                            invoice_id, email, request.user.email
                        ),
                        paypal_email=email,
                    )
                )
                ctx.update({'paypalform': paypal_form, 'email': email})

        return TemplateResponse(request, 'payments/test_paypal_email.html', ctx)

    def confirm_refund(self, request, pk):
        view = ConfirmRefundView.as_view(admin_site=self.admin_site)
        return view(request, pk=pk)

admin.site.register(PaypalBookingTransaction, PaypalBookingTransactionAdmin)
admin.site.unregister(PayPalIPN)
admin.site.register(PayPalIPN, PayPalAdmin)
