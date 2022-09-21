from django.urls import path
from .views import (
    stripe_payment_complete, stripe_webhook, UserInvoiceListView
)


app_name = 'stripe_payments'

urlpatterns = [
    path('stripe-payment-complete/', stripe_payment_complete, name="stripe_payment_complete"),
    path('stripe/webhook/', stripe_webhook, name="stripe_webhook"),
    path('account-transactions/', UserInvoiceListView.as_view(), name="user_invoices")
]
