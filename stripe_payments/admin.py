from django.contrib import admin

from stripe_payments.models import Invoice, Seller, StripePaymentIntent


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    ...


@admin.register(Seller)
class SellerAdmin(admin.ModelAdmin):
    ...

@admin.register(StripePaymentIntent)
class StripePaymentIntentAdmin(admin.ModelAdmin):
    ...
