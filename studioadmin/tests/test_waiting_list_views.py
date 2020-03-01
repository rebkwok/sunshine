from django.urls import reverse
from django.test import TestCase

from model_bakery import baker

from .helpers import TestPermissionMixin


class WaitingListViewStudioAdminTests(TestPermissionMixin, TestCase):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.url_string = 'studioadmin:event_waiting_list'

    def test_cannot_access_if_not_logged_in(self):
        """
        test that the page redirects if user is not logged in
        """
        event = baker.make_recipe('booking.future_PC')
        url = reverse(self.url_string, kwargs={'event_slug':event.slug})
        resp = self.client.get(url)
        redirected_url = reverse('account_login') + "?next={}".format(url)
        self.assertEqual(resp.status_code, 302)
        self.assertIn(redirected_url, resp.url)

    def test_cannot_access_if_not_staff(self):
        """
        test that the page redirects if user is not a staff user
        """
        event = baker.make_recipe('booking.future_PC')
        self.client.login(username=self.user.username, password="test")
        url = reverse(self.url_string, kwargs={'event_slug':event.slug})
        resp = self.client.get(url, kwargs={'event_slug':event.slug})
        redirected_url = reverse('admin:login') + "?next={}".format(url)
        self.assertEqual(resp.status_code, 302)
        self.assertIn(redirected_url, resp.url)

    def test_can_access_as_staff_user(self):
        """
        test that the page can be accessed by a staff user
        """
        event = baker.make_recipe('booking.future_PC')
        self.client.login(username=self.staff_user.username, password="test")
        resp = self.client.get(reverse(self.url_string, kwargs={'event_slug':event.slug}))
        self.assertEqual(resp.status_code, 200)

    def test_waiting_list_users_shown(self):
        """
        Only show users on the waiting list for the relevant event
        """
        self.client.login(username=self.staff_user.username, password="test")
        event = baker.make_recipe('booking.future_PC')
        event1 = baker.make_recipe('booking.future_PC')

        event_wl = baker.make_recipe(
            'booking.waiting_list_user', event=event, _quantity=3
        )
        baker.make_recipe(
            'booking.waiting_list_user', event=event1, _quantity=3
        )
        resp = self.client.get(reverse(self.url_string, kwargs={'event_slug':event.slug}))
        waiting_list_users = resp.context_data['waiting_list_users']
        self.assertEqual(set(waiting_list_users), set(event_wl))

    def test_remove_waiting_list_users(self):
        """
        Only show users on the waiting list for the relevant event
        """
        self.client.login(username=self.staff_user.username, password="test")
        event = baker.make_recipe('booking.future_PC')

        event_wl = baker.make_recipe(
            'booking.waiting_list_user', event=event, _quantity=3
        )
        resp = self.client.get(reverse(self.url_string, kwargs={'event_slug':event.slug}))
        waiting_list_users = resp.context_data['waiting_list_users']
        self.assertEqual(len(waiting_list_users), 3)

        resp = self.client.post(
            reverse(self.url_string, kwargs={'event_slug':event.slug}), data={'remove_user': [event_wl[0].id]}
        )

        waiting_list_users = resp.context_data['waiting_list_users']
        self.assertEqual(len(waiting_list_users), 2)
