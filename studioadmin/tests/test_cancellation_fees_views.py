# -*- coding: utf-8 -*-
from model_bakery import baker

from django.urls import reverse
from django.test import RequestFactory, TestCase

from .helpers import TestPermissionMixin


class CancellationFeesListViewTests(TestPermissionMixin, TestCase):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.url = reverse('studioadmin:outstanding_fees')

    def setUp(self):
        super().setUp()
        self.client.login(username=self.staff_user.username, password="test")

    def test_cannot_access_if_not_logged_in(self):
        """
        test that the page redirects if user is not logged in
        """
        self.client.logout()
        resp = self.client.get(self.url)
        redirected_url = reverse('account_login') + "?next={}".format(self.url)
        self.assertEqual(resp.status_code, 302)
        self.assertIn(redirected_url, resp.url)

    def test_can_access_as_staff_user(self):
        """
        test that the page can be accessed by a staff user
        """
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)

    def test_shows_cancellation_fees(self):
        pass


class UserCancellationFeesListViewTests(TestPermissionMixin, TestCase):

    def setUp(self):
        super().setUp()
        self.url = reverse('studioadmin:user_fees', args=[self.user.id])
        self.client.login(username=self.staff_user.username, password="test")

    def test_cannot_access_if_not_logged_in(self):
        """
        test that the page redirects if user is not logged in
        """
        self.client.logout()
        resp = self.client.get(self.url)
        redirected_url = reverse('account_login') + "?next={}".format(self.url)
        self.assertEqual(resp.status_code, 302)
        self.assertIn(redirected_url, resp.url)

    def test_can_access_as_staff_user(self):
        """
        test that the page can be accessed by a staff user
        """
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)

    def test_no_outstanding_fees(self):
        assert "done" == False

    def test_paid_outstanding_fees_not_shown(self):
        assert "done" == False

    def test_outstanding_fees_not_shown(self):
        assert "done" == False


class UserCancellationFeesAjaxTests(TestPermissionMixin, TestCase):

    def setUp(self):
        super().setUp()
        self.booking = baker.make_recipe("booking.booking", user=self.user)
        self.toggle_payment_url = reverse("studioadmin:ajax_toggle_cancellation_fee_payment", args=(self.booking.id,))
        self.toggle_remove_fee_url = reverse("studioadmin:ajax_toggle_remove_cancellation_fee", args=(self.booking.id,))
        self.payment_status_url = reverse("studioadmin:ajax_get_cancellation_fee_payment_status", args=(self.booking.id,))
        self.total_user_fees_url = reverse("studioadmin:ajax_get_user_total_fees", args=(self.user.id,))

    def test_toggle_cancellation_fee_payment(self):
        assert "done" == False

    def test_remove_cancellation_fee(self):
        assert "done" == False

    def test_get_cancellation_fee_payment_status(self):
        assert "done" == False

    def test_get_user_total_fees(self):
        assert "done" == False
