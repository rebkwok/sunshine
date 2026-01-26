# -*- coding: utf-8 -*-

from datetime import timedelta

from bs4 import BeautifulSoup
from model_bakery import baker

from django.urls import reverse
from django.utils import timezone
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
        # 2 fees due for self.user
        baker.make_recipe('booking.booking', event__cancellation_fee=1.00, user=self.user, cancellation_fee_incurred=True, _quantity=2)
        # 1 fee already paid
        baker.make_recipe('booking.booking', event__cancellation_fee=1.00, user=self.user, cancellation_fee_incurred=True, cancellation_fee_paid=True)
        user = baker.make_recipe('booking.user')
        # fees for another user
        baker.make_recipe('booking.booking', event__cancellation_fee=1.00, user=user, cancellation_fee_incurred=True, _quantity=4)

        resp = self.client.get(self.url)
        soup = BeautifulSoup(resp.content, 'html.parser')
        fees = soup.find_all("span", {"class": "fees-due"})
        self.assertEqual(len(fees), 2)

        fees_links = [
            user_fees.find("a").attrs["href"] for user_fees in fees
        ]
        fees_text = [
            user_fees.text.strip() for user_fees in fees
        ]
        for user in [self.user, user]:
            self.assertIn(f"/instructor-admin/fees/{self.user.id}/", fees_links)
            self.assertIn(f"£{user.outstanding_fees_total()}", fees_text)

    def test_long_user_email_abbreviated(self):
        user = baker.make_recipe('booking.user', email="averylongemailaddress@example.com")
        baker.make_recipe('booking.booking', event__cancellation_fee=1.00, user=user, cancellation_fee_incurred=True, _quantity=4)
        resp = self.client.get(self.url)
        content = resp.content.decode()
        assert "averylongemailaddress@..." in content
        assert "mailto:averylongemailaddress@example.com" in content


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
        resp = self.client.get(self.url)
        soup = BeautifulSoup(resp.content, 'html.parser')
        self.assertIn("No outstanding fees.", soup.text)

    def test_paid_outstanding_fees_not_shown(self):
        baker.make_recipe("booking.booking", user=self.user, cancellation_fee_incurred=True, cancellation_fee_paid=True)
        resp = self.client.get(self.url)
        soup = BeautifulSoup(resp.content, 'html.parser')
        self.assertIn("No outstanding fees.", soup.text)

    def test_outstanding_fees_shown(self):
        # paid_booking
        baker.make_recipe(
            "booking.booking", event__date=timezone.now() + timedelta(2), event__cancellation_fee=4.00,
            user=self.user, cancellation_fee_incurred=True, cancellation_fee_paid=True
        )
        # uppaid_bookings
        booking1 = baker.make_recipe(
            "booking.booking", event__date=timezone.now() + timedelta(2), event__cancellation_fee=3.00,
            user=self.user, cancellation_fee_incurred=True, cancellation_fee_paid=False
        )
        booking2 = baker.make_recipe(
            "booking.booking", event__date=timezone.now() + timedelta(2), event__cancellation_fee=5.00,
            user=self.user, cancellation_fee_incurred=True, cancellation_fee_paid=False
        )
        resp = self.client.get(self.url)
        soup = BeautifulSoup(resp.content, 'html.parser')
        fees = soup.find_all("td", {"class": "event-fee"})
        fee_texts = [fee.text for fee in fees]
        self.assertEqual(len(fees), 2)
        for booking in [booking1, booking2]:
            self.assertIn(f"£{booking.event.cancellation_fee:.2f}", fee_texts)

        total = soup.find("span", {"id": f"total-fees"})
        self.assertEqual(total.text, "8.00")


class UserCancellationFeesAjaxTests(TestPermissionMixin, TestCase):

    def setUp(self):
        super().setUp()
        self.booking = baker.make_recipe("booking.booking", event__cancellation_fee=1.00, user=self.user, cancellation_fee_incurred=True)
        self.toggle_payment_url = reverse("studioadmin:ajax_toggle_cancellation_fee_payment", args=(self.booking.id,))
        self.toggle_remove_fee_url = reverse("studioadmin:ajax_toggle_remove_cancellation_fee", args=(self.booking.id,))
        self.payment_status_url = reverse("studioadmin:ajax_get_cancellation_fee_payment_status", args=(self.booking.id,))
        self.total_user_fees_url = reverse("studioadmin:ajax_get_user_total_fees", args=(self.user.id,))
        self.client.login(username=self.staff_user.username, password="test")

    def test_toggle_cancellation_fee_payment(self):
        self.assertFalse(self.booking.cancellation_fee_paid)
        # toggle paid
        self.client.post(self.toggle_payment_url)
        self.booking.refresh_from_db()
        self.assertTrue(self.booking.cancellation_fee_paid)
        self.assertTrue(self.booking.cancellation_fee_incurred)
        self.assertEqual(self.user.outstanding_fees_total(), 0)
        # toggle unpaid
        self.client.post(self.toggle_payment_url)
        self.booking.refresh_from_db()
        self.assertFalse(self.booking.cancellation_fee_paid)
        self.assertTrue(self.booking.cancellation_fee_incurred)
        self.assertEqual(self.user.outstanding_fees_total(), 1.00)

    def test_remove_cancellation_fee(self):
        self.assertFalse(self.booking.cancellation_fee_paid)
        self.client.post(self.toggle_remove_fee_url)
        self.booking.refresh_from_db()
        self.assertFalse(self.booking.cancellation_fee_incurred)
        # add the fee back
        self.client.post(self.toggle_remove_fee_url)
        self.booking.refresh_from_db()
        self.assertTrue(self.booking.cancellation_fee_incurred)

    def test_remove_cancellation_fee_paid(self):
        # if fee is paid, removing the fee also sets unpaid to false
        self.booking.cancellation_fee_paid = True
        self.booking.save()
        self.client.post(self.toggle_remove_fee_url)
        self.booking.refresh_from_db()
        self.assertFalse(self.booking.cancellation_fee_incurred)
        self.assertFalse(self.booking.cancellation_fee_paid)

    def test_get_cancellation_fee_payment_status(self):
        resp = self.client.post(self.payment_status_url)
        soup = BeautifulSoup(resp.content, 'html.parser')
        payment_status = soup.find("label", {"class": "btn-fee-payment"})
        self.assertIn("Paid", payment_status.text)

    def test_get_user_total_fees(self):
        # shows fee total
        resp = self.client.post(self.total_user_fees_url)
        self.assertEqual(resp.json(), {'total_fees': "1.00"})

        # calculates from multiple bookings
        baker.make_recipe("booking.booking", event__cancellation_fee=5, user=self.user, cancellation_fee_incurred=True)
        resp = self.client.post(self.total_user_fees_url)
        self.assertEqual(resp.json(), {'total_fees': "6.00"})

        # doesn't include paid fees
        self.booking.cancellation_fee_paid = True
        self.booking.save()
        resp = self.client.post(self.total_user_fees_url)
        self.assertEqual(resp.json(), {'total_fees': "5.00"})
