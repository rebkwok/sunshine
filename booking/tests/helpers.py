from datetime import datetime
from datetime import timezone as dt_timezone

from importlib import import_module
import random

from model_bakery import baker

from django.contrib.auth.models import User
from django.conf import settings
from django.test import RequestFactory
from django.utils import timezone
from django.utils.html import strip_tags

from accounts.utils import has_active_data_privacy_agreement
from accounts.models import (
    ArchivedDisclaimer, DisclaimerContent, OnlineDisclaimer, DataPrivacyPolicy, SignedDataPrivacy
)


def _create_session():
    # create session
    settings.SESSION_ENGINE = 'django.contrib.sessions.backends.db'
    engine = import_module(settings.SESSION_ENGINE)
    store = engine.SessionStore()
    store.save()
    return store


class TestSetupMixin:
    @classmethod
    def setUpTestData(cls):
        cls.factory = RequestFactory()
        cls.user = User.objects.create_user(
            username='test', first_name="Test", last_name="User", email='test@test.com', password='test'
        )


def format_content(content):
    # strip tags, \n, \t and extra whitespace from content
    return ' '.join(
        strip_tags(content).replace('\n', '').replace('\t', '').split()
    )


def make_disclaimer_content(**kwargs):
    defaults = {
        "disclaimer_terms": f"test content {random.randint(0, 100000)}",
        "form": [],
        "version": None,
        "is_draft": False
    }
    data = {**defaults, **kwargs}
    return DisclaimerContent.objects.create(**data)


def make_online_disclaimer(**kwargs):
    if "version" not in kwargs:
        kwargs["version"] = DisclaimerContent.current_version()
    defaults = {
        "health_questionnaire_responses": [],
        "terms_accepted": True,
        "date_of_birth": datetime(2000, 1, 1, tzinfo=dt_timezone.utc),
        "phone": 123,
        "emergency_contact_name": "test",
        "emergency_contact_relationship": "test",
        "emergency_contact_phone": "123",
    }
    data = {**defaults, **kwargs}
    return OnlineDisclaimer.objects.create(**data)


def make_archived_disclaimer(**kwargs):
    if "version" not in kwargs:
        kwargs["version"] = DisclaimerContent.current_version()
    defaults = {
        "name": "Test User",
        "date_of_birth": datetime(1990, 6, 7, tzinfo=dt_timezone.utc),
        "date_archived": timezone.now(),
        "phone": "123455",
        "health_questionnaire_responses": [],
        "terms_accepted": True,
        "emergency_contact_name": "test",
        "emergency_contact_relationship": "test",
        "emergency_contact_phone": "123",
    }
    data = {**defaults, **kwargs}
    return ArchivedDisclaimer.objects.create(**data)


def make_data_privacy_agreement(user):
    if not has_active_data_privacy_agreement(user):
        if DataPrivacyPolicy.current_version() == 0:
            baker.make(DataPrivacyPolicy,content='Foo')
        baker.make(
            SignedDataPrivacy, user=user,
            version=DataPrivacyPolicy.current_version()
        )
