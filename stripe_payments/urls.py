from django.urls import path

from .connection_views import (
    StripeAuthorizeCallbackView,
    StripeAuthorizeView,
    connect_stripe_view,
)
from .views import stripe_payment_complete, stripe_webhook

app_name = "stripe_payments"

urlpatterns = [
    # connecting stripe seller account
    path("stripe/connect/", connect_stripe_view, name="connect_stripe"),
    path("stripe/authorize/", StripeAuthorizeView.as_view(), name="authorize_stripe"),
    path(
        "stripe/oauth/callback/",
        StripeAuthorizeCallbackView.as_view(),
        name="authorize_stripe_callback",
    ),
    # transactions
    path(
        "stripe-payment-complete/",
        stripe_payment_complete,
        name="stripe_payment_complete",
    ),
    path("stripe/webhook/", stripe_webhook, name="stripe_webhook"),
]
