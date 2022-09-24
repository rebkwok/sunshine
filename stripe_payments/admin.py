from django.contrib import admin
from django.urls import reverse
from django.utils.safestring import mark_safe 

from booking.models import Booking
from stripe_payments.models import Invoice, StripeRefund, StripePaymentIntent


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("invoice_id", "pi", "get_username", "display_amount", "paid", "items")

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
    exclude = ("client_secret",)

    def username(self, obj):
        return obj.invoice.username

    def inv(self, obj):
        return mark_safe(
            '<a href="{}">{}</a>'.format(
            reverse("admin:stripe_payments_invoice_change", args=(obj.invoice.pk,)),
            obj.invoice.invoice_id
        ))
    inv.short_description = "Invoice"

    def pi(self, obj):
        return mark_safe(
            '<a href="{}">{}</a>'.format(
            reverse("admin:stripe_payments_stripepaymentintent_change", args=(obj.payment_intent.pk,)),
            obj.payment_intent.payment_intent_id
        ))
    pi.short_description = "Payment Intent"

    def items(self, obj):
        return _inv_items(obj.invoice)


def _inv_items(invoice):
    items = sum(list(invoice.items_summary().values()), [])
    items = [f"<li>{item}</li>" for item in items]
    return mark_safe(f"<ul>{''.join(items)}</ul")


@admin.register(StripeRefund)
class StripeRefundAdmin(admin.ModelAdmin):
    list_display = ("refund_id", "pi", "inv", "username", "status", "booking")

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
        return mark_safe(
            '<a href="{}">{}</a>'.format(
            reverse("admin:booking_booking_change", args=(obj.booking_id,)),
            Booking.objects.get(id=obj.booking_id).event
        ))