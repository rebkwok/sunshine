from django.contrib import admin
from django.urls import reverse
from django.utils.safestring import mark_safe 

from booking.models import Booking, Membership, GiftVoucher
from stripe_payments.models import Invoice, StripeRefund, StripePaymentIntent


class BookingInline(admin.TabularInline):
    fields = ("id", "booking_reference", "user", "event", "status")
    readonly_fields = ("booking_reference", "user", "event", "status")
    model = Booking
    extra = 0
    can_delete = False
    
    def has_add_permission(self, request, obj):
        return False


class MembershipInline(admin.TabularInline):
    fields = ("user", "membership_type")
    readonly_fields = ("user", "membership_type")
    model = Membership
    extra = 0
    can_delete = False
    
    def has_add_permission(self, request, obj):
        return False


class GiftVoucherInline(admin.TabularInline):
    fields = ("purchaser_email", "voucher")
    readonly_fields = ("purchaser_email", "voucher")
    model = GiftVoucher
    extra = 0
    can_delete = False
    
    def has_add_permission(self, request, obj):
        return False
    

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("invoice_id", "pi", "get_username", "display_amount", "paid", "items")

    fields = (
        "invoice_id", "username", 
        "amount", "date_created", "paid", "date_paid",
        "total_voucher_code", "payment_intent_ids"
    )
    readonly_fields = fields

    inlines = (BookingInline, MembershipInline, GiftVoucherInline)

    def get_username(self, obj):
        return obj.username
    get_username.short_description = "Email"
    get_username.admin_order_field = "username"

    def display_amount(self, obj):
        return f"£{obj.amount}"
    display_amount.short_description = "amount"
    display_amount.admin_order_field = "amount"

    def pi(self, obj):
        if obj.payment_intents.exists():
            pi = obj.payment_intents.first()
            return mark_safe(
                '<a href="{}">{}</a>'.format(
                reverse("admin:stripe_payments_stripepaymentintent_change", args=(pi.pk,)),
                pi.payment_intent_id
            ))
        return ""
    pi.short_description = "Payment Intent"

    def items(self, obj):
        return _inv_items(obj)


@admin.register(StripePaymentIntent)
class StripePaymentIntentAdmin(admin.ModelAdmin):
    list_display = ("payment_intent_id", "inv", "username", "status", "items")
    exclude = ("client_secret","seller")
    fields = (
        "payment_intent_id", "amount", "description", "status", "invoice",
        "metadata", "currency" 
    )
    readonly_fields = fields

    def username(self, obj):
        return obj.invoice.username

    def inv(self, obj):
        return mark_safe(
            '<a href="{}">{}</a>'.format(
            reverse("admin:stripe_payments_invoice_change", args=(obj.invoice.pk,)),
            obj.invoice.invoice_id
        ))
    inv.short_description = "Invoice"

    def items(self, obj):
        return _inv_items(obj.invoice)


def _inv_items(invoice):
    items = sum(list(invoice.items_summary().values()), [])
    if items:
        items = [f"<li>{item}</li>" for item in items]
        return mark_safe(f"<ul>{''.join(items)}</ul>")
    return ""


@admin.register(StripeRefund)
class StripeRefundAdmin(admin.ModelAdmin):
    list_display = ("refund_id", "pi", "inv", "username", "status", "booking")

    fields = (
        "refund_id", "payment_intent", "invoice", "booking_id", "amount", "status", 
        "reason", "metadata", "currency" 
    )
    readonly_fields = fields
    exclude = ("seller",)

    def username(self, obj):
        return obj.invoice.username
    
    def inv(self, obj):
        return mark_safe(
            '<a href="{}">{}</a>'.format(
            reverse("admin:stripe_payments_invoice_change", args=(obj.invoice.pk,)),
            obj.invoice.invoice_id
        ))
    inv.short_description = "Original Invoice"

    def pi(self, obj):
        return mark_safe(
            '<a href="{}">{}</a>'.format(
            reverse("admin:stripe_payments_stripepaymentintent_change", args=(obj.payment_intent.pk,)),
            obj.payment_intent.payment_intent_id
        ))
    pi.short_description = "Payment Intent"

    def booking(self, obj):
        try:
            booking = Booking.objects.get(id=obj.booking_id)
            if booking:
                return mark_safe(
                    '<a href="{}">{}</a>'.format(
                    reverse("admin:booking_booking_change", args=(obj.booking_id,)),
                    booking.event
                ))
        except Booking.DoesNotExist:
            return f"{obj.booking_id} (deleted)"
