import pytest
from model_bakery import baker

from django.urls import reverse
from django.test import TestCase
from django.contrib.auth.models import User

from studioadmin.views.users import NAME_FILTERS
from .helpers import TestPermissionMixin
from booking.tests.helpers import make_disclaimer_content, make_online_disclaimer


class UserListViewTests(TestPermissionMixin, TestCase):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.url = reverse('studioadmin:user_list')

    def test_cannot_access_if_not_logged_in(self):
        """
        test that the page redirects if user is not logged in
        """
        resp = self.client.get(self.url)
        redirected_url = reverse('admin:login') + "?next={}".format(self.url)
        self.assertEqual(resp.status_code, 302)
        self.assertIn(redirected_url, resp.url)

    def test_cannot_access_if_not_staff(self):
        """
        test that the page redirects if user is not a staff user
        """
        self.client.login(username=self.user.username, password="test")
        resp = self.client.get(self.url)
        redirected_url = reverse('admin:login') + "?next={}".format(self.url)
        self.assertEqual(resp.status_code, 302)
        self.assertIn(redirected_url, resp.url)

    def test_can_access_as_staff_user(self):
        """
        test that the page can be accessed by a staff user
        """
        self.client.login(username=self.staff_user.username, password="test")
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)

    def test_all_users_are_displayed(self):
        baker.make_recipe('booking.user', _quantity=6)
        # 8 users total, incl self.user, self.staff_user
        self.assertEqual(User.objects.count(), 8)
        self.client.login(username=self.staff_user.username, password="test")
        resp = self.client.get(self.url)
        self.assertEqual(
            list(resp.context_data['users']), list(User.objects.all())
        )

    def test_abbreviations_for_long_username(self):
        """
        Usernames > 15 characters are split to 2 lines
        """
        baker.make_recipe(
            'booking.user',
            username='test123456789101112'
        )
        self.client.login(username=self.staff_user.username, password="test")
        resp = self.client.get(self.url)
        self.assertIn('test12345678-</br>9101112', resp.rendered_content)

    def test_abbreviations_for_long_names(self):
        """
        Names > 12 characters are split to 2 lines; names with hyphens are
        split on the first hyphen
        """
        baker.make_recipe(
            'booking.user',
            first_name='namewithmorethan12characters',
            last_name='name-with-three-hyphens'
        )
        self.client.login(username=self.staff_user.username, password="test")
        resp = self.client.get(self.url)
        self.assertIn(
            'namewith-</br>morethan12characters', resp.rendered_content
        )
        self.assertIn('name-</br>with-three-hyphens', resp.rendered_content)

    def test_user_filter(self):
        baker.make_recipe(
            'booking.user', username='FooBar', first_name='AUser',
            last_name='Bar'
        )
        baker.make_recipe(
            'booking.user', username='Testing1', first_name='aUser',
            last_name='Bar'
        )
        baker.make_recipe(
            'booking.user', username='Testing2', first_name='BUser',
            last_name='Bar'
        )
        self.client.login(username=self.staff_user.username, password="test")
        resp = self.client.get(self.url, {'filter': 'A'})
        self.assertEqual(len(resp.context_data['users']), 2)
        for user in resp.context_data['users']:
            self.assertTrue(user.first_name.upper().startswith('A'))

         # 5 users total, incl self.user, self.staff_user
        self.assertEqual(User.objects.count(), 5)
        resp = self.client.get(self.url, {'filter': 'All'})
        self.assertEqual(len(resp.context_data['users']), 5)

    def test_filter_options(self):
        # make a user with first name starting with all options
        for option in NAME_FILTERS:
            baker.make_recipe('booking.user', first_name='{}Usr'.format(option))
        # delete any starting with Z
        User.objects.filter(first_name__istartswith='Z').delete()
        self.client.login(username=self.staff_user.username, password="test")
        resp = self.client.get(self.url)
        filter_options = resp.context_data['filter_options']
        for opt in filter_options:
            if opt['value'] == 'Z':
                self.assertFalse(opt['available'])
            else:
                self.assertTrue(opt['available'])


@pytest.mark.django_db
def test_user_disclaimer_view_questionnaire_responses(client, superuser):
    user = baker.make(User)
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
            ]
    )
    make_online_disclaimer(
        user=user,
        health_questionnaire_responses={
            "Say something": "OK",
            'What is your favourite colour?': ["blue"]
        }
    )

    client.force_login(superuser)
    resp = client.get(
        reverse("studioadmin:user_disclaimer", args=(user.id,))
    )
    assert "<strong>Say something</strong><br/>OK<br/><strong>What is your favourite colour?</strong><br/>blue" in resp.rendered_content


@pytest.mark.django_db
def test_user_disclaimer_view_questionnaire_no_responses(client, superuser):
    user = baker.make(User)
    make_online_disclaimer(user=user)

    client.force_login(superuser)
    # confirm no errors if no questionnaire responses to display
    resp = client.get(
        reverse("studioadmin:user_disclaimer", args=(user.id,))
    )
    assert resp.status_code == 200
