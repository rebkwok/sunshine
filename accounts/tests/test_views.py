# -*- coding: utf-8 -*-
from datetime import timedelta

import pytest

from model_bakery import baker

from django.core.cache import cache
from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone

from allauth.account.models import EmailAddress

from ..models import (
    DataPrivacyPolicy,
    DisclaimerContent,
    OnlineDisclaimer,
    has_active_disclaimer,
)
from ..utils import has_active_data_privacy_agreement

from conftest import (
    make_disclaimer_content,
    make_online_disclaimer,
    make_data_privacy_agreement,
)

pytestmark = pytest.mark.django_db


def test_profile_update_view(client):
    """
    Test custom view to allow users to update their details
    """
    user = baker.make(
        User,
        username="test_user",
        first_name="Test",
        last_name="User",
    )
    url = reverse("accounts:update_profile")
    client.force_login(user)
    resp = client.get(url)
    assert resp.context_data["section"] == "account"


def test_profile_update_view_post(client):
    """
    Test custom view to allow users to update their details
    """
    user = baker.make(
        User,
        username="test_user",
        first_name="Test",
        last_name="User",
    )
    url = reverse("accounts:update_profile")
    client.force_login(user)
    client.post(
        url,
        {"username": user.username, "first_name": "Fred", "last_name": user.last_name},
    )
    user.refresh_from_db()
    assert user.first_name == "Fred"


def test_profile_view(client, configured_user):
    url = reverse("accounts:profile")
    client.force_login(configured_user)
    resp = client.get(url)
    assert resp.status_code == 200


def test_profile_view_requires_signed_data_privacy(client, user):
    baker.make(DataPrivacyPolicy)
    url = reverse("accounts:profile")
    client.force_login(user)
    resp = client.get(url)
    assert resp.status_code == 302
    assert reverse("accounts:data_privacy_review") in resp.url

    make_data_privacy_agreement(user)
    resp = client.get(url)
    assert resp.status_code == 200


class CustomLoginViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = User.objects.create(username="test_user", is_active=True)
        cls.user.set_password("password")
        cls.user.save()
        EmailAddress.objects.create(
            user=cls.user, email="test@gmail.com", primary=True, verified=True
        )

    def test_get_login_view(self):
        resp = self.client.get(reverse("account_login"))
        self.assertEqual(resp.status_code, 200)

    def test_post_login(self):
        resp = self.client.post(
            reverse("account_login"),
            {"login": self.user.username, "password": "password"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("accounts:profile"), resp.url)

    def test_login_from_password_change(self):
        # post with login username and password overrides next in request
        # params to return to profile
        resp = self.client.post(
            reverse("account_login") + "?next=/accounts/password/change/",
            {"login": self.user.username, "password": "password"},
        )

        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("accounts:profile"), resp.url)

        resp = self.client.post(
            reverse("account_login") + "?next=/accounts/password/set/",
            {"login": self.user.username, "password": "password"},
        )

        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("accounts:profile"), resp.url)


class DataPrivacyViewTests(TestCase):
    def test_get_data_privacy_view(self):
        # no need to be a logged in user to access
        resp = self.client.get(reverse("data_privacy_policy"))
        self.assertEqual(resp.status_code, 200)


class CookiePolicyViewTests(TestCase):
    def test_get_cookie_view(self):
        # no need to be a logged in user to access
        resp = self.client.get(reverse("cookie_policy"))
        self.assertEqual(resp.status_code, 200)


class SignedDataPrivacyCreateViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.url = reverse("accounts:data_privacy_review")
        cls.data_privacy_policy = baker.make(DataPrivacyPolicy, version=None)
        cls.user = User.objects.create_user(
            username="test", email="test@test.com", password="test"
        )
        make_data_privacy_agreement(cls.user)

    def setUp(self):
        super(SignedDataPrivacyCreateViewTests, self).setUp()
        self.client.login(username=self.user.username, password="test")

    def test_user_already_has_active_signed_agreement(self):
        # dp agreement is created in setup
        self.assertTrue(has_active_data_privacy_agreement(self.user))
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse("accounts:profile"))

        # make new policy
        cache.clear()
        baker.make(DataPrivacyPolicy, version=None)
        self.assertFalse(has_active_data_privacy_agreement(self.user))
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)

    def test_create_new_agreement(self):
        # make new policy
        cache.clear()
        baker.make(DataPrivacyPolicy, version=None)
        self.assertFalse(has_active_data_privacy_agreement(self.user))

        self.client.post(self.url, data={"confirm": True})
        self.assertTrue(has_active_data_privacy_agreement(self.user))


@pytest.fixture
def disclaimer_content():
    content = make_disclaimer_content(form=[{"label": "test", "type": "text"}])
    yield content


def get_disclaimer_form_data(user):
    return {
        "date_of_birth": "01-Jan-1990",
        "phone": "123445",
        "emergency_contact_name": "test1",
        "emergency_contact_relationship": "mother",
        "emergency_contact_phone": "4547",
        "terms_accepted": True,
        "health_questionnaire_responses_0": ["foo"],
        "password": "test",
        "user": user.id,
        "version": DisclaimerContent.current_version(),
    }


def test_disclaimer_create_view_login_required(client, user):
    url = reverse("accounts:disclaimer_form", args=(user.id,))
    resp = client.get(url)
    redirected_url = reverse("account_login") + "?next={}".format(url)
    assert resp.status_code == 302
    assert redirected_url in resp.url


def test_disclaimer_create_view_shows_msg_if_already_has_disclaimer(
    client, user, disclaimer_content
):
    make_online_disclaimer(user=user, version=disclaimer_content.version)
    client.force_login(user)
    url = reverse("accounts:disclaimer_form", args=(user.id,))
    assert has_active_disclaimer(user)
    resp = client.get(url)
    assert resp.status_code == 200

    assert "You have already completed a disclaimer." in str(resp.rendered_content)
    assert "Submit" not in str(resp.rendered_content)


def test_disclaimer_create_view_submitting_form_without_valid_password(
    client, user, disclaimer_content
):
    client.force_login(user)
    assert OnlineDisclaimer.objects.count() == 0
    url = reverse("accounts:disclaimer_form", args=(user.id,))
    resp = client.post(url, {**get_disclaimer_form_data(user), "password": "wrong"})
    form = resp.context_data["form"]
    assert form.errors == {"password": ["Invalid password entered"]}


def test_disclaimer_create_view_must_be_over_16(client, user, disclaimer_content):
    client.force_login(user)
    assert OnlineDisclaimer.objects.count() == 0
    url = reverse("accounts:disclaimer_form", args=(user.id,))
    resp = client.post(url, {**get_disclaimer_form_data(user), "terms_accepted": False})
    form = resp.context_data["form"]
    assert form.errors == {"terms_accepted": ["This field is required."]}


def test_disclaimer_create_view_terms_accepted(client, user, disclaimer_content):
    client.force_login(user)
    assert OnlineDisclaimer.objects.count() == 0
    url = reverse("accounts:disclaimer_form", args=(user.id,))
    resp = client.post(
        url, {**get_disclaimer_form_data(user), "date_of_birth": "01-Jan-2020"}
    )
    form = resp.context_data["form"]
    assert form.errors == {
        "date_of_birth": [
            "You must be at least 16 years old to register and book classes"
        ]
    }


def test_disclaimer_create_view_phone_number_validation(
    client, user, disclaimer_content
):
    client.force_login(user)
    assert OnlineDisclaimer.objects.count() == 0
    url = reverse("accounts:disclaimer_form", args=(user.id,))
    resp = client.post(url, {**get_disclaimer_form_data(user), "phone": "test"})
    form = resp.context_data["form"]
    assert form.errors == {
        "phone": ["Enter a valid phone number (no dashes or brackets)."]
    }


def test_disclaimer_create_view_health_questionnaire(client, user):
    client.force_login(user)
    content_with_questionnaire = make_disclaimer_content(
        form=[
            {
                "type": "text",
                "required": False,
                "label": "Say something",
                "name": "text-1",
                "subtype": "text",
            },
            {
                "type": "text",
                "required": True,
                "label": "What is your favourite colour?",
                "name": "text-2",
                "choices": ["red", "green", "blue"],
                "subtype": "text",
            },
        ]
    )
    make_online_disclaimer(user=user, version=content_with_questionnaire.version)
    url = reverse("accounts:disclaimer_form", args=(user.id,))
    resp = client.get(url)
    form = resp.context_data["form"]
    # disclaimer content questionnaire fields have been translated into form fields
    questionnaire_fields = form.fields["health_questionnaire_responses"].fields
    assert questionnaire_fields[0].label == "Say something"
    assert questionnaire_fields[0].initial is None
    assert questionnaire_fields[1].label == "What is your favourite colour?"


def test_disclaimer_create_view_submitting_form_creates_disclaimer(
    client, user, disclaimer_content
):
    client.force_login(user)
    assert OnlineDisclaimer.objects.count() == 0
    url = reverse("accounts:disclaimer_form", args=(user.id,))
    client.post(url, get_disclaimer_form_data(user))

    assert OnlineDisclaimer.objects.count() == 1

    # user now has disclaimer and can't re-access
    resp = client.get(url)
    assert resp.status_code == 200

    assert "You have already completed a disclaimer." in str(resp.rendered_content)
    assert "Submit" not in str(resp.rendered_content)


def test_disclaimer_create_view_health_questionnaire_required_fields(client, user):
    client.force_login(user)
    make_disclaimer_content(
        form=[
            {
                "type": "text",
                "required": False,
                "label": "Say something",
                "name": "text-1",
                "subtype": "text",
            },
            {
                "type": "text",
                "required": True,
                "label": "What is your favourite colour?",
                "name": "text-2",
                "choices": ["red", "green", "blue"],
                "subtype": "text",
            },
        ],
        version=None,  # make sure it's the latest
    )
    url = reverse("accounts:disclaimer_form", args=(user.id,))
    # form data only has response for qn 0 (not required)
    form_data = get_disclaimer_form_data(user)
    resp = client.post(url, form_data)
    assert resp.status_code == 200
    form = resp.context_data["form"]
    assert form.errors == {
        "health_questionnaire_responses": ["Please fill in all required fields."]
    }

    del form_data["health_questionnaire_responses_0"]
    form_data["health_questionnaire_responses_1"] = "red"
    resp = client.post(url, form_data)
    assert resp.status_code == 302


def test_disclaimer_create_view_updating_disclaimer_health_questionnaire(client, user):
    user1 = User.objects.create_user(
        username="test1", email="test1@test.com", password="test"
    )

    # health questionnaire fields that exist on the new disclaimer are prepopulated
    # skip choices fields that are different now
    # health form fields are extracted and set to expired disclaimer
    content_with_questionnaire = make_disclaimer_content(
        form=[
            {
                "type": "text",
                "required": False,
                "label": "Say something",
                "name": "text-1",
                "subtype": "text",
            },
            {
                "type": "select",
                "required": True,
                "label": "What is your favourite colour?",
                "name": "text-2",
                "values": [
                    {"label": "Red", "value": "red"},
                    {"label": "Green", "value": "green"},
                    {"label": "Blue", "value": "blue"},
                ],
                "subtype": "text",
            },
        ]
    )
    # make expired disclaimers with existing entries
    make_online_disclaimer(
        user=user,
        version=content_with_questionnaire.version,
        date=timezone.now() - timedelta(days=370),
        health_questionnaire_responses={
            "Say something": "OK",
            "What is your favourite colour?": ["blue"],
        },
    )
    make_online_disclaimer(
        user=user1,
        version=content_with_questionnaire.version,
        date=timezone.now() - timedelta(days=370),
        health_questionnaire_responses={
            "Say something": "Boo",
            "What is your favourite colour?": [
                "purple"
            ],  # not in new disclaimer choices
        },
    )
    client.force_login(user)
    url = reverse("accounts:disclaimer_form", args=(user.id,))
    resp = client.get(url)
    form = resp.context_data["form"]
    # disclaimer content questionnaire fields have been prepopulated
    questionnaire_fields = form.fields["health_questionnaire_responses"].fields
    assert questionnaire_fields[0].initial == "OK"
    assert questionnaire_fields[1].initial == ["blue"]

    client.force_login(user1)
    url = reverse("accounts:disclaimer_form", args=(user1.id,))
    resp = client.get(url)
    form = resp.context_data["form"]
    # disclaimer content questionnaire fields have been prepopulated
    questionnaire_fields = form.fields["health_questionnaire_responses"].fields
    assert questionnaire_fields[0].initial == "Boo"
    assert questionnaire_fields[1].initial is None


def test_disclaimer_update_view(client, user):
    # health questionnaire fields are prepopulated
    content_with_questionnaire = make_disclaimer_content(
        form=[
            {
                "type": "text",
                "required": False,
                "label": "Say something",
                "name": "text-1",
                "subtype": "text",
            },
            {
                "type": "text",
                "required": False,
                "label": "Say another thing",
                "name": "text-1",
                "subtype": "text",
            },
            {
                "type": "select",
                "required": True,
                "label": "What is your favourite colour?",
                "name": "text-2",
                "values": [
                    {"label": "Red", "value": "red"},
                    {"label": "Green", "value": "green"},
                    {"label": "Blue", "value": "blue"},
                ],
                "subtype": "text",
            },
        ]
    )
    # make disclaimers with existing entries for 2 questions
    make_online_disclaimer(
        user=user,
        version=content_with_questionnaire.version,
        health_questionnaire_responses={
            "Say something": "OK",
            "What is your favourite colour?": ["blue"],
        },
    )
    client.force_login(user)
    url = reverse("accounts:disclaimer_form_update", args=(user.id,))
    resp = client.get(url)
    form = resp.context_data["form"]
    # disclaimer content questionnaire fields have been prepopulated
    questionnaire_fields = form.fields["health_questionnaire_responses"].fields
    assert questionnaire_fields[0].initial == "OK"
    assert not questionnaire_fields[1].initial
    assert questionnaire_fields[2].initial == ["blue"]


def test_disclaimer_update_view_only_uses_active_disclaimer(
    client, user, disclaimer_content
):
    # health questionnaire fields are prepopulated
    make_disclaimer_content()
    # expired
    make_online_disclaimer(
        user=user,
        version=disclaimer_content.version,
        date=timezone.now() - timedelta(days=370),
    )
    client.force_login(user)
    url = reverse("accounts:disclaimer_form_update", args=(user.id,))
    resp = client.get(url)
    assert resp.status_code == 302
    assert resp.url == reverse("accounts:disclaimer_form", args=(user.id,))

    # no disclaimer
    user1 = baker.make(User)
    client.force_login(user1)
    url = reverse("accounts:disclaimer_form_update", args=(user1.id,))
    resp = client.get(url)
    assert resp.status_code == 302
    assert resp.url == reverse("accounts:disclaimer_form", args=(user1.id,))


def test_disclaimer_emergency_contact_update_view_get(client, user):
    disclaimer = make_online_disclaimer(
        user=user,
        phone="012",
        emergency_contact_name="test",
        emergency_contact_relationship="test",
        emergency_contact_phone="123",
    )
    # expired disclaimer
    make_online_disclaimer(
        user=user,
        date=timezone.now() - timedelta(days=370),
        phone="999",
        emergency_contact_name="test1",
        emergency_contact_relationship="test1",
        emergency_contact_phone="888",
    )
    client.force_login(user)
    url = reverse("accounts:update_emergency_contact", args=(user.id,))
    resp = client.get(url)
    form = resp.context_data["form"]
    # form includes data from active disclaimer
    assert form.instance == disclaimer


def test_disclaimer_emergency_contact_update_view_no_active_disclaimer(client, user):
    # expired disclaimer
    make_online_disclaimer(
        user=user,
        date=timezone.now() - timedelta(days=370),
        phone="999",
        emergency_contact_name="test1",
        emergency_contact_relationship="test1",
        emergency_contact_phone="888",
    )
    client.force_login(user)
    url = reverse("accounts:update_emergency_contact", args=(user.id,))
    resp = client.get(url)
    assert resp.status_code == 302
    assert resp.url == reverse("accounts:disclaimer_form", args=(user.id,))


def test_disclaimer_emergency_contact_update_view_post(client, user):
    disclaimer = make_online_disclaimer(
        user=user,
        phone="012",
        emergency_contact_name="test",
        emergency_contact_relationship="test",
        emergency_contact_phone="123",
    )
    client.force_login(user)
    url = reverse("accounts:update_emergency_contact", args=(user.id,))
    client.post(
        url,
        data=dict(
            phone="111",
            emergency_contact_name="test1",
            emergency_contact_relationship="test1",
            emergency_contact_phone="888",
        ),
    )
    disclaimer.refresh_from_db()
    assert disclaimer.phone == "111"
    assert disclaimer.emergency_contact_name == "test1"
    assert disclaimer.emergency_contact_relationship == "test1"
    assert disclaimer.emergency_contact_phone == "888"
