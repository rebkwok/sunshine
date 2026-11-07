import stripe
from django.apps import apps


def test_ready_configures_stripe(settings, monkeypatch):
    settings.STRIPE_SECRET_KEY = "test-secret-key"
    settings.STRIPE_API_VERSION = "2020-08-27"
    monkeypatch.setattr(stripe, "api_key", None)
    monkeypatch.setattr(stripe, "api_version", "unset")

    apps.get_app_config("stripe_payments").ready()

    assert stripe.api_key == "test-secret-key"
    assert stripe.api_version == "2020-08-27"
