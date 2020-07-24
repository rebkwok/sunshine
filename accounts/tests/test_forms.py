# -*- coding: utf-8 -*-
from datetime import datetime
from model_bakery import baker

from django.test import TestCase, override_settings
from django.contrib.auth.models import User, Group
from django.urls import reverse
from django.utils import timezone

from ..admin import CookiePolicyAdminForm, DataPrivacyPolicyAdminForm
from ..forms import DataPrivacyAgreementForm, SignupForm, DisclaimerForm
from ..models import CookiePolicy, DataPrivacyPolicy, SignedDataPrivacy


from booking.tests.helpers import TestSetupMixin, make_disclaimer_content, make_online_disclaimer


class SignUpFormTests(TestSetupMixin, TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.url = reverse('account_signup')
        super(SignUpFormTests, cls).setUpTestData()

    def setUp(self):
        self.form_data = {
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'test_user@test.com',
            'username': 'testuser',
            'password1': 'dj34nmadkl24', 'password2': 'dj34nmadkl24'
         }

    def test_signup_form(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)

    def test_get_signup_view_with_username(self):
        resp = self.client.get(self.url + "?username=test")
        self.assertEqual(
            resp.context_data['form'].fields['username'].initial, 'test'
        )

    def test_signup_form_with_invalid_data(self):
        # first_name must have 30 characters or fewer
        self.form_data.update(
            {
                'first_name': 'abcdefghijklmnopqrstuvwxyz12345',
                 'last_name': 'User'
            }
        )
        resp = self.client.post(self.url, self.form_data)
        self.assertFalse(resp.context_data['form'].is_valid())

    def test_sign_up(self):
        self.form_data.update({'first_name': 'New', 'last_name': 'Name'})
        self.client.post(self.url, self.form_data)
        user = User.objects.latest('id')
        self.assertEquals('New', user.first_name)
        self.assertEquals('Name', user.last_name)

    def test_signup_dataprotection_confirmation_required(self):
        baker.make(DataPrivacyPolicy)
        self.form_data.update({
            'first_name': 'Test',
            'last_name': 'User',
            'data_privacy_confirmation': False
        })
        form = SignupForm(data=self.form_data)
        self.assertFalse(form.is_valid())

    def test_sign_up_with_data_protection(self):
        dp = baker.make(DataPrivacyPolicy)
        self.assertFalse(SignedDataPrivacy.objects.exists())
        self.form_data.update(
            {
                'first_name': 'New',
                'last_name': 'Name',
                'data_privacy_confirmation': True
            }
        )
        self.client.post(self.url, self.form_data)
        user = User.objects.latest('id')
        self.assertEquals('New', user.first_name)
        self.assertEquals('Name', user.last_name)
        self.assertTrue(SignedDataPrivacy.objects.exists())
        self.assertEqual(user.data_privacy_agreement.first().version, dp.version)


class DisclaimerFormTests(TestSetupMixin, TestCase):

    form_data = {
        'emergency_contact_name': "test",
        'emergency_contact_relationship': "test",
        'emergency_contact_phone': "test",
        'terms_accepted': True,
        'password': 'password',
        'health_questionnaire_responses_0': "test"
    }

    def setUp(self):
        make_disclaimer_content(
            form=[
                    {
                        'type': 'text',
                        'required': False,
                        'label': 'Say something',
                        'name': 'text-1234',
                        'subtype': 'text'
                    }
                ]
        )

    def test_disclaimer_form(self):
        form = DisclaimerForm(data=self.form_data, disclaimer_user=self.user)
        assert form.is_valid()

    def test_terms_accepted_required(self):
        data = {**self.form_data, 'terms_accepted': False}
        form = DisclaimerForm(data=data, disclaimer_user=self.user)
        assert form.is_valid() is False
        assert form.errors == {'terms_accepted': ['This field is required.']}

    def test_with_expired_disclaimer(self):
        disclaimer = make_online_disclaimer(
            user=self.user,
            date=datetime(2015, 2, 10, 19, 0, tzinfo=timezone.utc),
            emergency_contact_name="Donald Duck",
            emergency_contact_relationship="Duck",
            emergency_contact_phone="123",
            health_questionnaire_responses={"Say something": "Boo"}
        )
        assert disclaimer.is_active is False

        form = DisclaimerForm(disclaimer_user=self.user)
        # initial fields set to expired disclaimer
        # Note health questionnaire fields are modified in the view after the form is instantiated
        assert form.fields['emergency_contact_name'].initial == 'Donald Duck'
        assert form.fields['emergency_contact_relationship'].initial == 'Duck'
        assert form.fields['emergency_contact_phone'].initial == '123'

        # terms accepted NOT set to expired
        assert form.fields['terms_accepted'].initial is None


class DataPrivacyAgreementFormTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = baker.make(User)
        baker.make(DataPrivacyPolicy)

    def test_confirm_required(self):
        form = DataPrivacyAgreementForm(next_url='/', data={'confirm': False})
        self.assertFalse(form.is_valid())

        form = DataPrivacyAgreementForm(next_url='/', data={'confirm': True})
        self.assertTrue(form.is_valid())


class CookiePolicyAdminFormTests(TestCase):

    def test_create_cookie_policy_version_help(self):
        form = CookiePolicyAdminForm()
        # version initial set to 1.0 for first policy
        self.assertEqual(form.fields['version'].help_text, '')
        self.assertEqual(form.fields['version'].initial, 1.0)

        baker.make(CookiePolicy, version=1.0)
        # help text added if updating
        form = CookiePolicyAdminForm()
        self.assertEqual(
            form.fields['version'].help_text,
            'Current version is 1.0.  Leave blank for next major version'
        )
        self.assertIsNone(form.fields['version'].initial)

    def test_validation_error_if_no_changes(self):
        policy = baker.make(CookiePolicy, version=1.0, content='Foo')
        form = CookiePolicyAdminForm(
            data={
                'content': 'Foo',
                'version': 1.5,
                'issue_date': policy.issue_date
            }
        )
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.non_field_errors(),
            [
                'No changes made from previous version; new version must '
                'update policy content'
            ]
        )


class DataPrivacyPolicyAdminFormTests(TestCase):

    def test_create_data_privacy_policy_version_help(self):
        form = DataPrivacyPolicyAdminForm()
        # version initial set to 1.0 for first policy
        self.assertEqual(form.fields['version'].help_text, '')
        self.assertEqual(form.fields['version'].initial, 1.0)

        baker.make(DataPrivacyPolicy, version=1.0)
        # help text added if updating
        form = DataPrivacyPolicyAdminForm()
        self.assertEqual(
            form.fields['version'].help_text,
            'Current version is 1.0.  Leave blank for next major version'
        )
        self.assertIsNone(form.fields['version'].initial)

    def test_validation_error_if_no_changes(self):
        policy = baker.make(DataPrivacyPolicy, version=1.0, content='Foo')
        form = DataPrivacyPolicyAdminForm(
            data={
                'content': 'Foo',
                'version': 1.5,
                'issue_date': policy.issue_date
            }
        )
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.non_field_errors(),
            [
                'No changes made from previous version; new version must '
                'update policy content'
            ]
        )
