# -*- coding: utf-8 -*-
from datetime import timedelta
from model_bakery import baker

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.contrib.auth.models import User, Group
from django.urls import reverse
from django.utils import timezone

from allauth.account.models import EmailAddress

from ..models import DataPrivacyPolicy, DisclaimerContent, OnlineDisclaimer, has_active_disclaimer,active_disclaimer_cache_key
from ..utils import has_active_data_privacy_agreement
from ..views import ProfileUpdateView, profile

from booking.tests.helpers import TestSetupMixin, make_disclaimer_content, make_online_disclaimer, make_data_privacy_agreement


class ProfileUpdateViewTests(TestSetupMixin, TestCase):

    def test_updating_user_data(self):
        """
        Test custom view to allow users to update their details
        """
        user = baker.make(User, username="test_user",
                          first_name="Test",
                          last_name="User",
                          )
        url = reverse('accounts:update_profile')
        request = self.factory.post(
            url, {'username': user.username,
                  'first_name': 'Fred', 'last_name': user.last_name}
        )
        request.user = user
        view = ProfileUpdateView.as_view()
        resp = view(request)
        updated_user = User.objects.get(username="test_user")
        self.assertEqual(updated_user.first_name, "Fred")


class ProfileTests(TestSetupMixin, TestCase):

    def _get_response(self, user):
        url = reverse('accounts:profile')
        request = self.factory.get(url)
        request.user = user
        return profile(request)

    def test_profile_view(self):
        resp = self._get_response(self.user)
        self.assertEqual(resp.status_code, 200)

    def test_profile_requires_signed_data_privacy(self):
        baker.make(DataPrivacyPolicy)
        resp = self._get_response(self.user)
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse('accounts:data_privacy_review'), resp.url)


class CustomLoginViewTests(TestSetupMixin, TestCase):

    @classmethod
    def setUpTestData(cls):
        super(CustomLoginViewTests, cls).setUpTestData()
        cls.user = User.objects.create(username='test_user', is_active=True)
        cls.user.set_password('password')
        cls.user.save()
        EmailAddress.objects.create(user=cls.user,
                                    email='test@gmail.com',
                                    primary=True,
                                    verified=True)

    def test_get_login_view(self):
        resp = self.client.get(reverse('account_login'))
        self.assertEqual(resp.status_code, 200)

    def test_post_login(self):
        resp = self.client.post(
            reverse('account_login'),
            {'login': self.user.username, 'password': 'password'}
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse('accounts:profile'), resp.url)

    def test_login_from_password_change(self):
        # post with login username and password overrides next in request
        # params to return to profile
        resp = self.client.post(
            reverse('account_login') + '?next=/accounts/password/change/',
            {'login': self.user.username, 'password': 'password'}
        )

        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse('accounts:profile'), resp.url)

        resp = self.client.post(
            reverse('account_login') + '?next=/accounts/password/set/',
            {'login': self.user.username, 'password': 'password'}
        )

        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse('accounts:profile'), resp.url)


class DataPrivacyViewTests(TestCase):

    def test_get_data_privacy_view(self):
        # no need to be a logged in user to access
        resp = self.client.get(reverse('data_privacy_policy'))
        self.assertEqual(resp.status_code, 200)


class CookiePolicyViewTests(TestCase):

    def test_get_cookie_view(self):
        # no need to be a logged in user to access
        resp = self.client.get(reverse('cookie_policy'))
        self.assertEqual(resp.status_code, 200)


class SignedDataPrivacyCreateViewTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.url = reverse('accounts:data_privacy_review')
        cls.data_privacy_policy = baker.make(DataPrivacyPolicy, version=None)
        cls.user = User.objects.create_user(
            username='test', email='test@test.com', password='test'
        )
        make_data_privacy_agreement(cls.user)

    def setUp(self):
        super(SignedDataPrivacyCreateViewTests, self).setUp()
        self.client.login(username=self.user.username, password='test')

    def test_user_already_has_active_signed_agreement(self):
        # dp agreement is created in setup
        self.assertTrue(has_active_data_privacy_agreement(self.user))
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse('accounts:profile'))

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

        self.client.post(self.url, data={'confirm': True})
        self.assertTrue(has_active_data_privacy_agreement(self.user))


class DisclaimerCreateViewTests(TestSetupMixin, TestCase):

    def setUp(self):
        self.user1 = User.objects.create_user(
            username='test1', email='test1@test.com', password='test'
        )
        self.content = make_disclaimer_content(
            form=[{"label": "test", "type": "text"}]
        )
        self.form_data = {
            "date_of_birth": '01-Jan-1990',
            "phone": '123445',
            'emergency_contact_name': 'test1',
            'emergency_contact_relationship': 'mother',
            'emergency_contact_phone': '4547',
            'terms_accepted': True,
            'health_questionnaire_responses_0': ["foo"],
            'password': 'test',
            'user': self.user.id,
            'version': DisclaimerContent.current_version(),
        }
        cache.clear()
        self.client.login(username=self.user.username, password="test")

    def test_login_required(self):
        self.client.logout()
        url = reverse('accounts:disclaimer_form', args=(self.user.id,))
        resp = self.client.get(url)
        redirected_url = reverse('account_login') + "?next={}".format(url)

        assert resp.status_code == 302
        assert redirected_url in resp.url

    def test_shows_msg_if_already_has_disclaimer(self):
        make_online_disclaimer(user=self.user, version=self.content.version)
        self.client.force_login(self.user)
        url = reverse('accounts:disclaimer_form', args=(self.user.id,))
        assert has_active_disclaimer(self.user)
        resp = self.client.get(url)
        assert resp.status_code == 200

        assert "You have already completed a disclaimer." in str(resp.rendered_content)
        assert "Submit" not in str(resp.rendered_content)

    def test_submitting_form_without_valid_password(self):
        assert OnlineDisclaimer.objects.count() == 0
        url = reverse('accounts:disclaimer_form', args=(self.user.id,))
        resp = self.client.post(url, {**self.form_data, "password": "wrong"})
        form = resp.context_data["form"]
        assert form.errors == {"password": ['Invalid password entered']}

    def test_must_be_over_16(self):
        assert OnlineDisclaimer.objects.count() == 0
        url = reverse('accounts:disclaimer_form', args=(self.user.id,))
        resp = self.client.post(url, {**self.form_data, "terms_accepted": False})
        form = resp.context_data["form"]
        assert form.errors == {"terms_accepted": ['This field is required.']}

    def test_terms_accepted(self):
        assert OnlineDisclaimer.objects.count() == 0
        url = reverse('accounts:disclaimer_form', args=(self.user.id,))
        resp = self.client.post(url, {**self.form_data, "date_of_birth": '01-Jan-2020'})
        form = resp.context_data["form"]
        assert form.errors == {"date_of_birth": ["You must be at least 16 years old to register and book classes"]}

    def test_phone_number_validation(self):
        assert OnlineDisclaimer.objects.count() == 0
        url = reverse('accounts:disclaimer_form', args=(self.user.id,))
        resp = self.client.post(url, {**self.form_data, "phone": 'test'})
        form = resp.context_data["form"]
        assert form.errors == {"phone": ['Enter a valid phone number (no dashes or brackets).']}

    def test_disclaimer_health_questionnaire(self):
        content_with_questionnaire = make_disclaimer_content(
            form=[
                    {
                        'type': 'text',
                        'required': False,
                        'label': 'Say something',
                        'name': 'text-1',
                        'subtype': 'text'
                    },
                    {
                        'type': 'text',
                        'required': True,
                        'label': 'What is your favourite colour?',
                        'name': 'text-2',
                        'choices': ["red", "green", "blue"],
                        'subtype': 'text'
                    }
                ]
        )
        make_online_disclaimer(user=self.user, version=content_with_questionnaire.version)
        url = reverse('accounts:disclaimer_form', args=(self.user.id,))
        resp = self.client.get(url)
        form = resp.context_data["form"]
        # disclaimer content questionnaire fields have been translated into form fields
        questionnaire_fields = form.fields['health_questionnaire_responses'].fields
        assert questionnaire_fields[0].label == "Say something"
        # text field initial is set to "-"
        assert questionnaire_fields[0].initial == "-"
        assert questionnaire_fields[1].label == "What is your favourite colour?"


    def test_submitting_form_creates_disclaimer(self):
        assert OnlineDisclaimer.objects.count() == 0
        url = reverse('accounts:disclaimer_form', args=(self.user.id,))
        self.client.post(url, self.form_data)

        assert OnlineDisclaimer.objects.count() == 1

        # user now has disclaimer and can't re-access
        resp = self.client.get(url)
        assert resp.status_code == 200

        assert "You have already completed a disclaimer." in str(resp.rendered_content)
        assert "Submit" not in str(resp.rendered_content)

    def test_disclaimer_health_questionnaire_required_fields(self):
        make_disclaimer_content(
            form=[
                    {
                        'type': 'text',
                        'required': False,
                        'label': 'Say something',
                        'name': 'text-1',
                        'subtype': 'text'
                    },
                    {
                        'type': 'text',
                        'required': True,
                        'label': 'What is your favourite colour?',
                        'name': 'text-2',
                        'choices': ["red", "green", "blue"],
                        'subtype': 'text'
                    }
                ],
            version=None  # make sure it's the latest
        )
        url = reverse('accounts:disclaimer_form', args=(self.user.id,))
        # form data only has response for qn 0 (not required)
        resp = self.client.post(url, self.form_data)
        assert resp.status_code == 200
        form = resp.context_data["form"]
        assert form.errors == {"health_questionnaire_responses": ["Please fill in all required fields."]}

        form_data = self.form_data
        del form_data["health_questionnaire_responses_0"]
        form_data["health_questionnaire_responses_1"] = "red"
        resp = self.client.post(url, {**form_data})
        assert resp.status_code == 302

    def test_updating_disclaimer_health_questionnaire(self):
        # health questionnaire fields that exist on the new disclaimer are prepopulated
        # skip choices fields that are different now
        # health form fields are extracted and set to expired disclaimer
        content_with_questionnaire = make_disclaimer_content(
            form=[
                    {
                        'type': 'text',
                        'required': False,
                        'label': 'Say something',
                        'name': 'text-1',
                        'subtype': 'text'
                    },
                    {
                        'type': 'select',
                        'required': True,
                        'label': 'What is your favourite colour?',
                        'name': 'text-2',
                        'values': [
                            {"label": "Red", "value": "red"},
                            {"label": "Green", "value": "green"},
                            {"label": "Blue", "value": "blue"},
                        ],
                        'subtype': 'text'
                    }
                ]
        )
        # make expired disclaimers with existing entries
        make_online_disclaimer(
            user=self.user, version=content_with_questionnaire.version,
            date=timezone.now() - timedelta(days=370),
            health_questionnaire_responses={
                "Say something": "OK",
                'What is your favourite colour?': ["blue"]
            }
        )
        make_online_disclaimer(
            user=self.user1, version=content_with_questionnaire.version,
            date=timezone.now() - timedelta(days=370),
            health_questionnaire_responses={
                "Say something": "Boo",
                'What is your favourite colour?': ["purple"]  # not in new disclaimer choices
            }
        )
        url = reverse('accounts:disclaimer_form', args=(self.user.id,))
        resp = self.client.get(url)
        form = resp.context_data["form"]
        # disclaimer content questionnaire fields have been prepopulated
        questionnaire_fields = form.fields['health_questionnaire_responses'].fields
        assert questionnaire_fields[0].initial == "OK"
        assert questionnaire_fields[1].initial == ["blue"]

        self.client.login(usernmae=self.user1.username, password="test")
        url = reverse('accounts:disclaimer_form', args=(self.user1.id,))
        resp = self.client.get(url)
        form = resp.context_data["form"]
        # disclaimer content questionnaire fields have been prepopulated
        questionnaire_fields = form.fields['health_questionnaire_responses'].fields
        assert questionnaire_fields[0].initial == "Boo"
        assert questionnaire_fields[1].initial is None
