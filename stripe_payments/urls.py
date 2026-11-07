from django.urls import path

from .connection_views import (
    authorize_stripe_callback_view,
    authorize_stripe_view,
    connect_stripe_view,
    disconnect_stripe_view,
)
from .views import stripe_payment_complete, stripe_webhook

app_name = "stripe_payments"

urlpatterns = [
    # connecting stripe seller account
    path("stripe/connect/", connect_stripe_view, name="connect_stripe"),
    path("stripe/authorize/", authorize_stripe_view, name="authorize_stripe"),
    path(
        "stripe/oauth/callback/",
        authorize_stripe_callback_view,
        name="authorize_stripe_callback",
    ),
    path("stripe/disconnect/", disconnect_stripe_view, name="disconnect_stripe"),
    # transactions
    path(
        "stripe-payment-complete/",
        stripe_payment_complete,
        name="stripe_payment_complete",
    ),
    path("stripe/webhook/", stripe_webhook, name="stripe_webhook"),
]
