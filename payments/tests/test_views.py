from model_bakery import baker

from django.core.cache import cache
from django.core import mail
from django.urls import reverse
from django.test import TestCase

from paypal.standard.ipn.models import PayPalIPN

from booking.models import Booking

from .helpers import TestPermissionMixin


class TestViews(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.url = reverse('payments:paypal_confirm')

    def test_confirm_return(self):
        booking = baker.make(Booking, event__name='Event1')
        resp = self.client.post(
            self.url,
            {
                'custom': 'booking {}'.format(booking.id),
                'payment_status': 'paid',
                'item_name': 'Event1'
            }
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context_data['obj_type'], 'booking')
        self.assertEqual(resp.context_data['obj'], booking)

    def test_confirm_return_with_unknown_obj(self):
        resp = self.client.post(
            self.url,
            {
                'custom': 'other',
                'payment_status': 'paid',
                'item_name': 'Foo'
            }
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context_data['obj_unknown'], True)
        self.assertIn(
            'Everything is probably fine...',
            resp.rendered_content
        )

    def test_confirm_return_with_no_custom_field(self):
        resp = self.client.post(
            self.url,
            {
                'payment_status': 'paid',
                'item_name': 'Event'
            }
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context_data['obj_unknown'], True)
        self.assertIn(
            'Everything is probably fine...',
            resp.rendered_content
        )

    def test_confirm_return_with_paypal_test(self):
        url = reverse('payments:paypal_confirm')
        resp = self.client.post(
            url,
            {
                'custom': 'paypal_test 0 testpp@test.com_123456 '
                          'testpp@test.com testpp@test.com '
                          'user@test.com',
                'payment_status': 'paid',
                'item_name': 'paypal_test'
            }
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp.context_data['test_paypal_email'], 'testpp@test.com'
        )
        self.assertIn(
            'The test payment is being processed',
            resp.rendered_content
        )

    def test_confirm_return_with_paypal_test_and_valid_ipn(self):
        url = reverse('payments:paypal_confirm')
        baker.make(
            PayPalIPN, invoice='testpp@test.com_123456',
            payment_status='Completed'
        )
        resp = self.client.post(
            url,
            {
                'custom': 'paypal_test 0 testpp@test.com_123456 '
                          'testpp@test.com user@test.com',
                'payment_status': 'paid',
                'item_name': 'paypal_test'
            }
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp.context_data['test_paypal_email'], 'testpp@test.com'
        )
        self.assertIn(
            'The test payment has completed successfully',
            resp.rendered_content
        )

    def test_cancel_return(self):
        url = reverse('payments:paypal_cancel')
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 200)


class ConfirmRefundViewTests(TestPermissionMixin, TestCase):

    def setUp(self):
        super(ConfirmRefundViewTests, self).setUp()
        self.booking = baker.make_recipe(
            'booking.booking', user=self.user,
            paid=True)
        self.url = reverse('admin:confirm_refund', args=[self.booking.id])

    def test_confirm_refund_for_paid_booking(self):
        """
        test that the page can be accessed by a staff user
        """
        self.assertTrue(self.booking.paid)
        self.client.login(username=self.superuser.username, password='test')
        resp = self.client.post(self.url, {'confirmed': ['Confirm']})

        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse('admin:index'))
        booking = Booking.objects.get(id=self.booking.id)
        self.assertFalse(booking.paid)
        self.assertEqual(len(mail.outbox), 1)

    def test_cancel_confirm_form(self):
        """
        test that page redirects without changes if cancel button used
        """
        self.assertTrue(self.booking.paid)
        self.client.login(username=self.superuser.username, password='test')
        resp = self.client.post(self.url, {'cancelled': ['Cancel']})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse('admin:index'))
        booking = Booking.objects.get(id=self.booking.id)
        self.assertTrue(booking.paid)
        self.assertEqual(len(mail.outbox), 0)


class TestPaypalViewTests(TestPermissionMixin, TestCase):


    def test_post_created_paypal_form(self):
        url = reverse('admin:test_paypal_email')
        self.client.login(username=self.superuser.username, password='test')
        resp = self.client.post(url, {'email': 'testpp@test.com'})
        self.assertEqual(resp.status_code, 200)

        self.assertIn('paypalform', resp.context_data)
        paypal_data = resp.context_data['paypalform'].initial

        self.assertTrue(paypal_data['invoice'].startswith('testpp@test.com'))
        # invoice is email plus '_' and 6 char uuid
        self.assertEqual(len(paypal_data['invoice']), len('testpp@test.com') + 7)
        self.assertEqual(paypal_data['amount'], 0.01)
        self.assertEqual(
            paypal_data['custom'],
            'paypal_test 0 {} testpp@test.com test@test.com'.format(
                paypal_data['invoice']
            )
        )

    def test_post_with_no_email_address(self):
        url = reverse('admin:test_paypal_email')
        self.client.login(username=self.superuser.username, password='test')
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 200)

        self.assertNotIn('paypalform', resp.context_data)
        self.assertIn('email_errors', resp.context_data)
        self.assertEqual(
            resp.context_data['email_errors'],
            'Please enter an email address to test'
        )

