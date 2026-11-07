import stripe
from django.apps import AppConfig
from django.conf import settings


class StripePaymentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "stripe_payments"

    def ready(self):
        stripe.api_key = settings.STRIPE_SECRET_KEY
        stripe.api_version = settings.STRIPE_API_VERSION
