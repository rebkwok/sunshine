# -*- coding: utf-8 -*-

from model_mommy import mommy

from django.test import TestCase, override_settings
from django.contrib.auth.models import User, Group
from django.core.urlresolvers import reverse

from allauth.account.models import EmailAddress

from accounts.forms import SignupForm
from accounts.views import ProfileUpdateView, profile

from booking.tests.helpers import TestSetupMixin


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
