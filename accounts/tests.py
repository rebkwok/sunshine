# -*- coding: utf-8 -*-

from decimal import Decimal
from model_mommy import mommy

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.contrib.auth.models import User, Group
from django.urls import reverse

from allauth.account.models import EmailAddress

from .admin import CookiePolicyAdminForm, DataPrivacyPolicyAdminForm
from .forms import DataPrivacyAgreementForm, SignupForm
from .models import CookiePolicy, DataPrivacyPolicy, SignedDataPrivacy
from .utils import active_data_privacy_cache_key, \
    has_active_data_privacy_agreement
from .views import ProfileUpdateView, profile

from booking.tests.helpers import TestSetupMixin


def make_data_privacy_agreement(user):
    if not has_active_data_privacy_agreement(user):
        if DataPrivacyPolicy.current_version() == 0:
            mommy.make(DataPrivacyPolicy,content='Foo')
        mommy.make(
            SignedDataPrivacy, user=user,
            version=DataPrivacyPolicy.current_version()
        )


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
        mommy.make(DataPrivacyPolicy)
        self.form_data.update({
            'first_name': 'Test',
            'last_name': 'User',
            'data_privacy_confirmation': False
        })
        form = SignupForm(data=self.form_data)
        self.assertFalse(form.is_valid())

    def test_sign_up_with_data_protection(self):
        dp = mommy.make(DataPrivacyPolicy)
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


class ProfileUpdateViewTests(TestSetupMixin, TestCase):

    def test_updating_user_data(self):
        """
        Test custom view to allow users to update their details
        """
        user = mommy.make(User, username="test_user",
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
        self.assertEquals(updated_user.first_name, "Fred")


class ProfileTests(TestSetupMixin, TestCase):

    def _get_response(self, user):
        url = reverse('accounts:profile')
        request = self.factory.get(url)
        request.user = user
        return profile(request)

    def test_profile_view(self):
        resp = self._get_response(self.user)
        self.assertEquals(resp.status_code, 200)

    def test_profile_requires_signed_data_privacy(self):
        mommy.make(DataPrivacyPolicy)
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


class DataPrivacyPolicyModelTests(TestCase):

    def test_no_policy_version(self):
        self.assertEqual(DataPrivacyPolicy.current_version(), 0)

    def test_policy_versioning(self):
        self.assertEqual(DataPrivacyPolicy.current_version(), 0)

        DataPrivacyPolicy.objects.create(content='Foo')
        self.assertEqual(DataPrivacyPolicy.current_version(), Decimal('1.0'))

        DataPrivacyPolicy.objects.create(content='Foo1')
        self.assertEqual(DataPrivacyPolicy.current_version(), Decimal('2.0'))

        DataPrivacyPolicy.objects.create(content='Foo2', version=Decimal('2.6'))
        self.assertEqual(DataPrivacyPolicy.current_version(), Decimal('2.6'))

        DataPrivacyPolicy.objects.create(content='Foo3')
        self.assertEqual(DataPrivacyPolicy.current_version(), Decimal('3.0'))

    def test_cannot_make_new_version_with_same_content(self):
        DataPrivacyPolicy.objects.create(content='Foo')
        self.assertEqual(DataPrivacyPolicy.current_version(), Decimal('1.0'))
        with self.assertRaises(ValidationError):
            DataPrivacyPolicy.objects.create(content='Foo')

    def test_policy_str(self):
        dp = DataPrivacyPolicy.objects.create(content='Foo')
        self.assertEqual(
            str(dp), 'Data Privacy Policy - Version {}'.format(dp.version)
        )


class CookiePolicyModelTests(TestCase):

    def test_policy_versioning(self):
        CookiePolicy.objects.create(content='Foo')
        self.assertEqual(CookiePolicy.current().version, Decimal('1.0'))

        CookiePolicy.objects.create(content='Foo1')
        self.assertEqual(CookiePolicy.current().version, Decimal('2.0'))

        CookiePolicy.objects.create(content='Foo2', version=Decimal('2.6'))
        self.assertEqual(CookiePolicy.current().version, Decimal('2.6'))

        CookiePolicy.objects.create(content='Foo3')
        self.assertEqual(CookiePolicy.current().version, Decimal('3.0'))

    def test_cannot_make_new_version_with_same_content(self):
        CookiePolicy.objects.create(content='Foo')
        self.assertEqual(CookiePolicy.current().version, Decimal('1.0'))
        with self.assertRaises(ValidationError):
            CookiePolicy.objects.create(content='Foo')

    def test_policy_str(self):
        dp = CookiePolicy.objects.create(content='Foo')
        self.assertEqual(
            str(dp), 'Cookie Policy - Version {}'.format(dp.version)
        )


class SignedDataPrivacyModelTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        DataPrivacyPolicy.objects.create(content='Foo')

    def setUp(self):
        self.user = mommy.make_recipe('booking.user')

    def test_cached_on_save(self):
        make_data_privacy_agreement(self.user)
        self.assertTrue(cache.get(active_data_privacy_cache_key(self.user)))

        DataPrivacyPolicy.objects.create(content='New Foo')
        self.assertFalse(has_active_data_privacy_agreement(self.user))

    def test_delete(self):
        make_data_privacy_agreement(self.user)
        self.assertTrue(cache.get(active_data_privacy_cache_key(self.user)))

        SignedDataPrivacy.objects.get(user=self.user).delete()
        self.assertIsNone(cache.get(active_data_privacy_cache_key(self.user)))


class DataPrivacyAgreementFormTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = mommy.make(User)
        mommy.make(DataPrivacyPolicy)

    def test_confirm_required(self):
        form = DataPrivacyAgreementForm(next_url='/', data={'confirm': False})
        self.assertFalse(form.is_valid())

        form = DataPrivacyAgreementForm(next_url='/', data={'confirm': True})
        self.assertTrue(form.is_valid())


class SignedDataPrivacyCreateViewTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.url = reverse('accounts:data_privacy_review')
        cls.data_privacy_policy = mommy.make(DataPrivacyPolicy, version=None)
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
        mommy.make(DataPrivacyPolicy, version=None)
        self.assertFalse(has_active_data_privacy_agreement(self.user))
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)

    def test_create_new_agreement(self):
        # make new policy
        cache.clear()
        mommy.make(DataPrivacyPolicy, version=None)
        self.assertFalse(has_active_data_privacy_agreement(self.user))

        self.client.post(self.url, data={'confirm': True})
        self.assertTrue(has_active_data_privacy_agreement(self.user))


class CookiePolicyAdminFormTests(TestCase):

    def test_create_cookie_policy_version_help(self):
        form = CookiePolicyAdminForm()
        # version initial set to 1.0 for first policy
        self.assertEqual(form.fields['version'].help_text, '')
        self.assertEqual(form.fields['version'].initial, 1.0)

        mommy.make(CookiePolicy, version=1.0)
        # help text added if updating
        form = CookiePolicyAdminForm()
        self.assertEqual(
            form.fields['version'].help_text,
            'Current version is 1.0.  Leave blank for next major version'
        )
        self.assertIsNone(form.fields['version'].initial)

    def test_validation_error_if_no_changes(self):
        policy = mommy.make(CookiePolicy, version=1.0, content='Foo')
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

        mommy.make(DataPrivacyPolicy, version=1.0)
        # help text added if updating
        form = DataPrivacyPolicyAdminForm()
        self.assertEqual(
            form.fields['version'].help_text,
            'Current version is 1.0.  Leave blank for next major version'
        )
        self.assertIsNone(form.fields['version'].initial)

    def test_validation_error_if_no_changes(self):
        policy = mommy.make(DataPrivacyPolicy, version=1.0, content='Foo')
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
