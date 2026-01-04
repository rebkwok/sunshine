# -*- coding: utf-8 -*-
import json
from datetime import datetime
from model_bakery import baker

import pytest

from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse

from ..admin import CookiePolicyAdminForm, DataPrivacyPolicyAdminForm, DisclaimerContentAdminForm
from ..forms import DataPrivacyAgreementForm, SignupForm
from ..models import CookiePolicy, DataPrivacyPolicy, SignedDataPrivacy, DisclaimerContent


from booking.tests.helpers import TestSetupMixin
from conftest import make_disclaimer_content


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
            'email2': 'test_user@test.com',
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
        self.assertEqual('New', user.first_name)
        self.assertEqual('Name', user.last_name)

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
        self.assertEqual('New', user.first_name)
        self.assertEqual('Name', user.last_name)
        self.assertTrue(SignedDataPrivacy.objects.exists())
        self.assertEqual(user.data_privacy_agreement.first().version, dp.version)


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


@pytest.mark.django_db
def test_disclaimer_content_admin_form_new():
    # Creating a new disclaimer
    form = DisclaimerContentAdminForm()
    # version not required, we set it automatically if not provided
    assert not form.fields["version"].required
    # no existing disclaimer, default to v 1.0
    assert not DisclaimerContent.objects.exists()
    assert form.fields['version'].initial == 1.0 


@pytest.mark.django_db
def test_disclaimer_content_admin_form_existing_draft():
    content = make_disclaimer_content(is_draft=True)
    form = DisclaimerContentAdminForm(instance=content)
    assert form.fields["version"].required is False
    # custom initial/help text not set for an existing instance
    assert not form.fields['version'].initial
    assert not form.fields['version'].help_text


@pytest.mark.django_db
def test_disclaimer_content_admin_form_new_with_previous_version():
    content = make_disclaimer_content()
    assert content.version == 1.0
    # Creating a new disclaimer
    form = DisclaimerContentAdminForm()
    # version not required, we set it automatically if not provided
    assert not form.fields["version"].required
    # existing disclaimer, default to next major version
    assert form.fields['version'].help_text == f'Current version is 1.0.  Leave blank for next major version (2.0)' 


@pytest.mark.django_db
def test_disclaimer_content_admin_form_new_with_previous_version():
    content = make_disclaimer_content()
    assert content.version == 1.0
    # Creating a new disclaimer
    form = DisclaimerContentAdminForm()
    # version not required, we set it automatically if not provided
    assert not form.fields["version"].required
    # existing disclaimer, default to next major version
    assert form.fields['version'].help_text == f'Current version is 1.0.  Leave blank for next major version (2.0)' 


@pytest.mark.django_db
def test_disclaimer_content_admin_form_valid():
    # Creating a new disclaimer
    form = DisclaimerContentAdminForm(
        data={"is_draft": False, "disclaimer_terms": "terms", "issue_date": datetime.today()}
    )
    # no version is valid as field not required
    assert form.is_valid()

    # but can also provide arbitrary version
    form = DisclaimerContentAdminForm(
        data={"is_draft": False, "disclaimer_terms": "terms", "issue_date": datetime.today(), "version": 3.8}
    )
    assert form.is_valid()


@pytest.mark.django_db
def test_disclaimer_content_admin_form_bad_version():
    content = make_disclaimer_content()
    assert content.version == 1.0
    # Creating a new disclaimer
    form = DisclaimerContentAdminForm(
        data={"is_draft": False, "version": 1.0, "disclaimer_terms": "terms", "issue_date": datetime.today()}
    )
    assert not form.is_valid()
    assert form.errors == {'version': ['New version must increment current version (must be greater than 1.0)']}


@pytest.mark.django_db
def test_disclaimer_content_admin_form_content_must_change_no_questionnaire():
    content = make_disclaimer_content(disclaimer_terms="terms")
    assert content.version == 1.0
    # Creating a new disclaimer
    form = DisclaimerContentAdminForm(
        data={"is_draft": False, "version": 2.0, "disclaimer_terms": "terms", "issue_date": datetime.today()}
    )
    assert not form.is_valid()
    assert form.non_field_errors() == ['No changes made from previous version; new version must update disclaimer content']


@pytest.mark.django_db
def test_disclaimer_content_admin_form_content_must_change():
    questionnaire_form = [
        {
            'type': 'text',
            'required': False,
            'label': 'Say something',
            'name': 'text-1',
            'subtype': 'text'
        },
    ]
    content = make_disclaimer_content(disclaimer_terms="terms", form=questionnaire_form)
    assert content.version == 1.0
    
    # no changes to form or terms
    form = DisclaimerContentAdminForm(
        data={
            "is_draft": False, 
            "version": 2.0, 
            "disclaimer_terms":  "terms", 
            "issue_date": datetime.today(),
            "form": json.dumps(questionnaire_form)
        }
    )
    assert not form.is_valid()
    assert form.non_field_errors() == ['No changes made from previous version; new version must update disclaimer content']

    # changes to form
    new_questionnaire_form = [
        {
            'type': 'text',
            'required': False,
            'label': 'Say another thing',
            'name': 'text-1',
            'subtype': 'text'
        },
    ]
    form = DisclaimerContentAdminForm(
        data={
            "is_draft": False, 
            "version": 2.0, 
            "disclaimer_terms":  "terms", 
            "issue_date": datetime.today(),
            "form": json.dumps(new_questionnaire_form)
        }
    )
    assert form.is_valid()

    # changes to terms
    form = DisclaimerContentAdminForm(
        data={
            "is_draft": False, 
            "version": 2.0, 
            "disclaimer_terms":  "new terms", 
            "issue_date": datetime.today(),
            "form": json.dumps(questionnaire_form)
        }
    )
    assert form.is_valid()
