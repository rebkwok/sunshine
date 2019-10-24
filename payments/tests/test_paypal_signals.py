# -*- coding: utf-8 -*-

from model_bakery import baker
from unittest.mock import Mock, patch

from django.conf import settings
from django.core import mail
from django.urls import reverse
from django.test import TestCase, override_settings

from paypal.standard.ipn.models import PayPalIPN

from six import b, text_type
from six.moves.urllib.parse import urlencode

from booking.models import Booking

from ..models import create_paypal_transaction, PaypalBookingTransaction
from ..models import logger as payment_models_logger


# Parameters are all bytestrings, so we can construct a bytestring
# request the same way that Paypal does.
CHARSET = "windows-1252"
TEST_RECEIVER_EMAIL = 'dummy-email@hotmail.com'
IPN_POST_PARAMS = {
    "mc_gross": b"20.00",
    "invoice": b"hrVegYKLardQ7JwAkBUgKX-inv001",
    "protection_eligibility": b"Ineligible",
    "txn_id": b"51403485VH153354B",
    "last_name": b"User",
    "receiver_email": b(TEST_RECEIVER_EMAIL),
    "payer_id": b"BN5JZ2V7MLEV4",
    "tax": b"0.00",
    "payment_date": b"23:04:06 Feb 02, 2009 PST",
    "first_name": b"Test",
    "mc_fee": b"0.44",
    "notify_version": b"3.8",
    "custom": b"video 1",
    "payer_status": b"verified",
    "payment_status": b"Completed",
    "business": b(TEST_RECEIVER_EMAIL),
    "quantity": b"1",
    "verify_sign": b"An5ns1Kso7MWUdW4ErQKJJJ4qi4-AqdZy6dD.sGO3sDhTf1wAbuO2IZ7",
    "payer_email": b"test_user@gmail.com",
    "payment_type": b"instant",
    "payment_fee": b"",
    "receiver_id": b"258DLEHY2BDK6",
    "txn_type": b"web_accept",
    "item_name": "Workshop",
    "mc_currency": b"GBP",
    "item_number": b"",
    "residence_country": "GB",
    "handling_amount": b"0.00",
    "charset": b(CHARSET),
    "payment_gross": b"",
    "transaction_subject": b"",
    "ipn_track_id": b"1bd9fe52f058e",
    "shipping": b"0.00",
}


@override_settings(DEFAULT_PAYPAL_EMAIL=TEST_RECEIVER_EMAIL)
class PaypalSignalsTests(TestCase):

    def paypal_post(self, params):
        """
        Does an HTTP POST the way that PayPal does, using the params given.
        Taken from django-paypal
        """
        # We build params into a bytestring ourselves, to avoid some encoding
        # processing that is done by the test client.
        cond_encode = lambda v: v.encode(CHARSET) if isinstance(v, text_type) else v
        byte_params = {
            cond_encode(k): cond_encode(v) for k, v in params.items()
            }
        post_data = urlencode(byte_params)
        return self.client.post(
            reverse('paypal-ipn'),
            post_data, content_type='application/x-www-form-urlencoded'
        )

    def test_paypal_notify_url_with_no_data(self):
        self.assertFalse(PayPalIPN.objects.exists())
        resp = self.paypal_post(
            {'charset': b(CHARSET), 'txn_id': 'test'}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(PayPalIPN.objects.count(), 1)

        ppipn = PayPalIPN.objects.first()
        self.assertTrue(ppipn.flag)

        # one warning email sent
        self.assertEqual(len(mail.outbox), 1)

        self.assertEqual(
            mail.outbox[0].subject,
            'WARNING! Error processing Invalid Payment Notification from PayPal'
        )
        self.assertEqual(
            mail.outbox[0].body,
            'PayPal sent an invalid transaction notification while '
            'attempting to process payment;.\n\nThe flag '
            'info was "{}"\n\nAn additional error was raised: {}'.format(
                ppipn.flag_info, 'Unknown object for payment'
            )
        )

    def test_paypal_notify_url_with_unknown_obj_type(self):
        self.assertFalse(PayPalIPN.objects.exists())
        resp = self.paypal_post(
            {'charset': b(CHARSET), 'custom': b'other 1', 'txn_id': b'test'}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(PayPalIPN.objects.count(), 1)

        ppipn = PayPalIPN.objects.first()
        self.assertTrue(ppipn.flag)

        # one warning email sent
        self.assertEqual(len(mail.outbox), 1)

        self.assertEqual(
            mail.outbox[0].subject,
            'WARNING! Error processing Invalid Payment Notification from PayPal'
        )
        self.assertEqual(
            mail.outbox[0].body,
            'PayPal sent an invalid transaction notification while '
            'attempting to process payment;.\n\nThe flag '
            'info was "{}"\n\nAn additional error was raised: {}'.format(
                ppipn.flag_info, 'Unknown object type other'
            )
        )

    def test_paypal_notify_url_with_no_matching_booking(self):
        self.assertFalse(PayPalIPN.objects.exists())

        resp = self.paypal_post(
            {'custom': b'booking 1', 'charset': b(CHARSET), 'txn_id': 'test'}
        )

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(PayPalIPN.objects.count(), 1)
        ppipn = PayPalIPN.objects.first()

        # one warning email sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            mail.outbox[0].subject,
            'WARNING! Error processing Invalid Payment Notification from PayPal'
        )
        self.assertEqual(
            mail.outbox[0].body,
            'PayPal sent an invalid transaction notification while '
            'attempting to process payment;.\n\nThe flag '
            'info was "{}"\n\nAn additional error was raised: {}'.format(
                ppipn.flag_info, 'Booking with id 1 does not exist'
            )
        )

    @patch('paypal.standard.ipn.models.PayPalIPN._postback')
    def test_paypal_notify_url_with_complete_status(self, mock_postback):
        mock_postback.return_value = b"VERIFIED"
        booking = baker.make(Booking, event__name='Workshop',
                             event__paypal_email=TEST_RECEIVER_EMAIL,
                             user__email='test@test.com')
        pptrans = create_paypal_transaction(booking.user, booking)

        self.assertFalse(PayPalIPN.objects.exists())
        params = dict(IPN_POST_PARAMS)
        params.update(
            {
                'custom': b('booking {}'.format(booking.id)),
                'invoice': b(pptrans.invoice_id),
                'txn_id': b'test_txn_id'
            }
        )
        self.assertIsNone(pptrans.transaction_id)
        resp = self.paypal_post(params)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(PayPalIPN.objects.count(), 1)
        ppipn = PayPalIPN.objects.first()
        self.assertFalse(ppipn.flag)
        self.assertEqual(ppipn.flag_info, '')

        # check paypal trans obj is updated
        pptrans.refresh_from_db()
        self.assertEqual(pptrans.transaction_id, 'test_txn_id')

        # 1 email sent to user
        self.assertEqual(len(mail.outbox), 1)

    @patch('paypal.standard.ipn.models.PayPalIPN._postback')
    def test_paypal_notify_url_with_complete_status_unmatching_object(self, mock_postback):
        mock_postback.return_value = b"VERIFIED"

        self.assertFalse(PayPalIPN.objects.exists())
        self.assertFalse(Booking.objects.exists())
        params = dict(IPN_POST_PARAMS)
        params.update(
            {
                'custom': b'booking 1',
            }
        )
        resp = self.paypal_post(params)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(PayPalIPN.objects.count(), 1)
        ppipn = PayPalIPN.objects.first()

        # paypal ipn is not flagged
        self.assertFalse(ppipn.flag)
        self.assertEqual(ppipn.flag_info, '')

        # we can't match up the payment to booking, so raise error and send
        # emails
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            mail.outbox[0].subject,
            'WARNING! Error processing PayPal IPN'
        )
        self.assertEqual(
            mail.outbox[0].body,
            'Valid Payment Notification received from PayPal but an error '
            'occurred during processing.\n\nTransaction id {}\n\nThe flag info '
            'was "{}"\n\nError raised: Booking with id 1 does not exist'.format(
                ppipn.txn_id, ppipn.flag_info,
            )
        )

    @patch('paypal.standard.ipn.models.PayPalIPN._postback')
    def test_successful_paypal_payment_sends_emails(self, mock_postback):
        mock_postback.return_value = b"VERIFIED"
        booking = baker.make(
            Booking, event__name='Workshop', user__email='testpp@test.com',
            event__paypal_email=TEST_RECEIVER_EMAIL
        )
        pptrans = create_paypal_transaction(booking.user, booking)
        invoice_id = pptrans.invoice_id

        self.assertFalse(PayPalIPN.objects.exists())
        params = dict(IPN_POST_PARAMS)
        params.update(
            {
                'custom': b('booking {}'.format(booking.id)),
                'invoice': b(invoice_id)
            }
        )
        resp = self.paypal_post(params)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(PayPalIPN.objects.count(), 1)

        # 1 email sent to user
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [booking.user.email])

    @patch('paypal.standard.ipn.models.PayPalIPN._postback')
    def test_successful_paypal_payment_updates_booking(self, mock_postback):
        mock_postback.return_value = b"VERIFIED"
        booking = baker.make(
            Booking, event__name='Workshop',
            event__paypal_email=TEST_RECEIVER_EMAIL
        )
        pptrans = create_paypal_transaction(booking.user, booking)
        invoice_id = pptrans.invoice_id
        self.assertFalse(booking.paid)
        self.assertFalse(PayPalIPN.objects.exists())
        params = dict(IPN_POST_PARAMS)
        params.update(
            {
                'custom': b('booking {}'.format(booking.id)),
                'invoice': b(invoice_id)
            }
        )
        self.paypal_post(params)
        booking.refresh_from_db()
        self.assertTrue(booking.paid)

    @patch('paypal.standard.ipn.models.PayPalIPN._postback')
    def test_paypal_notify_only_updates_relevant_booking(self, mock_postback):
        mock_postback.return_value = b"VERIFIED"
        booking = baker.make(
            Booking, event__name='Workshop', user__email='testpp@test.com',
            event__paypal_email=TEST_RECEIVER_EMAIL
        )
        pptrans = create_paypal_transaction(booking.user, booking)
        invoice_id = pptrans.invoice_id
        baker.make(
            Booking, event__name='Workshop',
            event__paypal_email=TEST_RECEIVER_EMAIL, _quantity=5
        )

        self.assertFalse(PayPalIPN.objects.exists())
        params = dict(IPN_POST_PARAMS)
        params.update(
            {
                'custom': b('booking {}'.format(booking.id)),
                'invoice': b(invoice_id)
            }
        )
        resp = self.paypal_post(params)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(PayPalIPN.objects.count(), 1)
        ppipn = PayPalIPN.objects.first()
        self.assertFalse(ppipn.flag)
        self.assertEqual(ppipn.flag_info, '')

        booking.refresh_from_db()
        self.assertTrue(booking.paid)
        # 1 emails sent to user
        self.assertEqual(len(mail.outbox), 1)

        for bk in Booking.objects.exclude(id=booking.id):
            self.assertFalse(bk.paid)

    @patch('paypal.standard.ipn.models.PayPalIPN._postback')
    def test_paypal_notify_url_with_complete_status_no_invoice_number(
            self, mock_postback
    ):
        mock_postback.return_value = b"VERIFIED"
        booking = baker.make(
            Booking, event__name='Workshop',
            event__paypal_email=TEST_RECEIVER_EMAIL,
            user__email='test@test.com'
        )

        self.assertFalse(PayPalIPN.objects.exists())
        params = dict(IPN_POST_PARAMS)
        params.update(
            {
                'custom': b('booking {}'.format(booking.id)),
                'invoice': b''
            }
        )
        self.paypal_post(params)
        booking.refresh_from_db()
        self.assertTrue(booking.paid)

        # 2 emails sent - user, support to notify about missing inv
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(
            mail.outbox[1].subject,
            '{} No invoice number on paypal ipn for booking id {}'.format(
                settings.ACCOUNT_EMAIL_SUBJECT_PREFIX, booking.id
            )
        )

    @patch('paypal.standard.ipn.models.PayPalIPN._postback')
    def test_paypal_notify_url_without_trans_object(self, mock_postback):
        """
        A PayPalEntryTransaction object should be created
        when the paypal form button is created (to generate and store the inv
        number and transaction id).  In case it isn't,
        we create one when processing the payment
        """
        mock_postback.return_value = b"VERIFIED"
        booking = baker.make(
            Booking, event__name='Workshop',
            event__paypal_email=TEST_RECEIVER_EMAIL,
            user__email='test@test.com'
        )

        self.assertFalse(PayPalIPN.objects.exists())
        self.assertFalse(PaypalBookingTransaction.objects.exists())

        params = dict(IPN_POST_PARAMS)
        params.update(
            {
                'custom': b('booking {}'.format(booking.id)),
                'invoice': b''
            }
        )
        resp = self.paypal_post(params)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(PayPalIPN.objects.count(), 1)
        ppipn = PayPalIPN.objects.first()
        self.assertFalse(ppipn.flag)
        self.assertEqual(ppipn.flag_info, '')

        self.assertEqual(PaypalBookingTransaction.objects.count(), 1)
        booking.refresh_from_db()
        self.assertTrue(booking.paid)
        # 2 emails sent, to user and support because there is no inv
        self.assertEqual(len(mail.outbox), 2)

    @patch('paypal.standard.ipn.models.PayPalIPN._postback')
    def test_paypal_notify_url_with_duplicate_trans_object(self, mock_postback):
        mock_postback.return_value = b"VERIFIED"
        booking = baker.make(Booking, event__name='Workshop',
                             event__paypal_email=TEST_RECEIVER_EMAIL,
                             user__email='test@test.com')
        booking1 = baker.make(
            Booking, event__paypal_email=TEST_RECEIVER_EMAIL,
            user__email='test1@test.com'
        )

        # create 2 paypal trans objects and make they for the same object
        pptrans = create_paypal_transaction(booking.user, booking)
        pptrans1 = create_paypal_transaction(booking.user, booking1)
        pptrans1.booking = booking
        pptrans1.save()

        self.assertEqual(PayPalIPN.objects.count(), 0)
        self.assertEqual(PaypalBookingTransaction.objects.count(), 2)

        params = dict(IPN_POST_PARAMS)
        params.update(
            {
                'custom': b('booking {}'.format(booking.id)),
                'invoice': b('{}'.format(pptrans.invoice_id))
            }
        )
        resp = self.paypal_post(params)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(PayPalIPN.objects.count(), 1)
        ppipn = PayPalIPN.objects.first()
        self.assertFalse(ppipn.flag)
        self.assertEqual(ppipn.flag_info, '')

        self.assertEqual(PaypalBookingTransaction.objects.count(), 2)
        booking.refresh_from_db()
        self.assertTrue(booking.paid)
        # 1 emails sent, to user only
        self.assertEqual(len(mail.outbox), 1)

    @patch('paypal.standard.ipn.models.PayPalIPN._postback')
    def test_paypal_notify_url_duplicate_trans_not_invoice(self, mock_postback):
        mock_postback.return_value = b"VERIFIED"
        booking = baker.make(Booking, event__name='Workshop',
                             event__paypal_email=TEST_RECEIVER_EMAIL,
                             user__email='test@test.com')
        booking1 = baker.make(Booking, event__name='Workshop',
                              event__paypal_email=TEST_RECEIVER_EMAIL,
                              user__email='test@test.com')

        # create 2 paypal trans objects and make they for the same object
        pptrans = create_paypal_transaction(booking.user, booking)
        pptrans1 = create_paypal_transaction(booking.user, booking1)
        pptrans1.booking = booking
        pptrans1.save()

        self.assertEqual(PayPalIPN.objects.count(), 0)
        self.assertEqual(PaypalBookingTransaction.objects.count(), 2)

        params = dict(IPN_POST_PARAMS)
        params.update(
            {
                'custom': b('booking {}'.format(booking.id)),
                'invoice': b''
            }
        )
        resp = self.paypal_post(params)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(PayPalIPN.objects.count(), 1)
        ppipn = PayPalIPN.objects.first()
        self.assertFalse(ppipn.flag)
        self.assertEqual(ppipn.flag_info, '')

        self.assertEqual(PaypalBookingTransaction.objects.count(), 2)
        booking.refresh_from_db()
        self.assertTrue(booking.paid)
        # 2 emails sent, to user and support because there is no inv
        self.assertEqual(len(mail.outbox), 2)

    @patch('paypal.standard.ipn.models.PayPalIPN._postback')
    def test_paypal_notify_url_with_refunded_status(self, mock_postback):
        """
        when a paypal payment is refunded, it looks like it posts back to the
        notify url again (since the PayPalIPN is updated).  Test that we can
        identify and process refunded payments.
        """
        mock_postback.return_value = b"VERIFIED"
        booking = baker.make(
            Booking, event__name='Workshop',
            event__paypal_email=TEST_RECEIVER_EMAIL
        )
        pptrans = create_paypal_transaction(booking.user, booking)
        pptrans.transaction_id = "test_trans_id"
        pptrans.save()

        self.assertFalse(PayPalIPN.objects.exists())
        params = dict(IPN_POST_PARAMS)
        params.update(
            {
                'custom': b('booking {}'.format(booking.id)),
                'invoice': b(pptrans.invoice_id),
                'payment_status': b'Refunded'
            }
        )
        self.paypal_post(params)
        booking.refresh_from_db()
        self.assertFalse(booking.paid)

        self.assertEqual(len(mail.outbox), 1,)

        # emails sent to support
        self.assertEqual(mail.outbox[0].to, [settings.SUPPORT_EMAIL])
        self.assertEqual(
            mail.outbox[0].subject,
            '{} Payment refund processed; booking id {}, ref {}'.format(
            settings.ACCOUNT_EMAIL_SUBJECT_PREFIX, booking.id,
            booking.booking_reference)
        )

    @patch('paypal.standard.ipn.models.PayPalIPN._postback')
    def test_paypal_date_format_with_extra_spaces(self, mock_postback):
        mock_postback.return_value = b"VERIFIED"
        booking = baker.make(Booking, event__name='Workshop',
                             event__paypal_email=TEST_RECEIVER_EMAIL)
        pptrans = create_paypal_transaction(booking.user, booking)
        pptrans.transaction_id = "test_trans_id"
        pptrans.save()

        params = dict(IPN_POST_PARAMS)
        params.update(
            {
                "payment_date": b"01:21:32  Jan   25  2015 PDT",
                'invoice': b(pptrans.invoice_id),
                'custom': b('booking {}'.format(booking.id))
            }
        )

        # Check extra spaces
        self.paypal_post(params)
        ppipn = PayPalIPN.objects.latest('id')
        self.assertFalse(ppipn.flag)

    def test_paypal_notify_url_with_invalid_date(self):
        """
        There has been one instance of a returned payment which has no info
        except a flag invalid date in the paypal form.  Check that this will
        send a support email
        """
        self.assertFalse(PayPalIPN.objects.exists())
        self.paypal_post(
            {
                "payment_date": b"2015-10-25 01:21:32",
                'charset': b(CHARSET),
                'txn_id': 'test',
            }
        )
        ppipn = PayPalIPN.objects.first()
        self.assertTrue(ppipn.flag)
        self.assertEqual(
            ppipn.flag_info,
            'Invalid form. (payment_date: Invalid date format '
            '2015-10-25 01:21:32: not enough values to unpack (expected 5, got 2))'
        )

        self.assertEqual(mail.outbox[0].to, [settings.SUPPORT_EMAIL])
        self.assertEqual(
            mail.outbox[0].subject,
            'WARNING! Error processing Invalid Payment Notification from PayPal'
        )
        self.assertEqual(
            mail.outbox[0].body,
            'PayPal sent an invalid transaction notification while attempting '
            'to process payment;.\n\nThe flag info was "Invalid form. '
            '(payment_date: Invalid date format '
            '2015-10-25 01:21:32: not enough values to unpack (expected 5, got 2))"'
            '\n\nAn additional error was raised: Unknown object for '
            'payment'
        )

    def test_paypal_notify_url_with_invalid_date_formats(self):
        """
        Check other invalid date formats
        %H:%M:%S %b. %d, %Y PDT is the expected format

        """
        # Fails because 25th cannot be convered to int
        self.paypal_post(
            {
                "payment_date": b"01:21:32 Jan 25th 2015 PDT",
                'charset': b(CHARSET),
                'txn_id': 'test'
            }
        )
        ppipn = PayPalIPN.objects.latest('id')
        self.assertTrue(ppipn.flag)
        self.assertEqual(
            ppipn.flag_info,
            "Invalid form. (payment_date: Invalid date format "
            "01:21:32 Jan 25th 2015 PDT: invalid literal for int() with "
            "base 10: '25th')"
        )

        # Fails because month is not in Mmm format
        self.paypal_post(
            {
                "payment_date": b"01:21:32 01 25 2015 PDT",
                'charset': b(CHARSET),
                'txn_id': 'test'
            }
        )
        ppipn = PayPalIPN.objects.latest('id')
        self.assertTrue(ppipn.flag)
        self.assertEqual(
            ppipn.flag_info,
            "Invalid form. (payment_date: Invalid date format "
            "01:21:32 01 25 2015 PDT: '01' is not in list)"
        )

        # Fails because month is not in Mmm format
        self.paypal_post(
            {
                "payment_date": b"01:21:32 January 25 2015 PDT",
                'charset': b(CHARSET),
                'txn_id': 'test'
            }
        )
        ppipn = PayPalIPN.objects.latest('id')
        self.assertTrue(ppipn.flag)
        self.assertEqual(
            ppipn.flag_info,
            "Invalid form. (payment_date: Invalid date format "
            "01:21:32 January 25 2015 PDT: 'January' is not in list)"
        )

        # Fails because year part cannot be convered to int
        self.paypal_post(
            {
                "payment_date": b"01:21:32 Jan 25 2015a PDT",
                'charset': b(CHARSET),
                'txn_id': 'test'
            }
        )
        ppipn = PayPalIPN.objects.latest('id')
        self.assertTrue(ppipn.flag)
        self.assertEqual(
            ppipn.flag_info,
            "Invalid form. (payment_date: Invalid date format "
            "01:21:32 Jan 25 2015a PDT: invalid literal for int() with "
            "base 10: '2015a')"
        )

        # No seconds part; fails on splitting the time
        self.paypal_post(
            {
                "payment_date": b"01:28 Jan 25 2015 PDT",
                'charset': b(CHARSET),
                'txn_id': 'test'
            }
        )
        ppipn = PayPalIPN.objects.latest('id')
        self.assertTrue(ppipn.flag)
        self.assertEqual(
            ppipn.flag_info,
            "Invalid form. (payment_date: Invalid date format "
            "01:28 Jan 25 2015 PDT: not enough values to unpack (expected 3, got 2))"
        )

        # Can be split and day/month/year parts converted but invalid date so
        #  conversion to datetime sails
        self.paypal_post(
            {
                "payment_date": b"01:21:32 Jan 49 2015 PDT",
                'charset': b(CHARSET),
                'txn_id': 'test'
            }
        )
        ppipn = PayPalIPN.objects.latest('id')
        self.assertTrue(ppipn.flag)
        self.assertEqual(
            ppipn.flag_info,
            "Invalid form. (payment_date: Invalid date format "
            "01:21:32 Jan 49 2015 PDT: day is out of range for month)"
        )

    @patch('paypal.standard.ipn.models.PayPalIPN._postback')
    def test_payment_received_with_duplicate_txn_flag(self, mock_postback):
        """
        If we get a flagged completed payment, send a warning email.  Most
        likely to happen with a duplicate transaction id
        """
        mock_postback.return_value = b"VERIFIED"
        booking = baker.make(Booking, event__name='Workshop',
                             event__paypal_email=TEST_RECEIVER_EMAIL)
        pptrans = create_paypal_transaction(booking.user, booking)
        # make an existing completed paypal ipn
        baker.make(PayPalIPN, txn_id='test_txn_id', payment_status='Completed')
        self.assertEqual(PayPalIPN.objects.count(), 1)

        params = dict(IPN_POST_PARAMS)
        params.update(
            {
                'custom': b('booking {}'.format(booking.id)),
                'invoice': b(pptrans.invoice_id),
                'txn_id': 'test_txn_id'
            }
        )
        self.paypal_post(params)
        booking.refresh_from_db()
        ppipn = PayPalIPN.objects.all()[0]
        ppipn1 = PayPalIPN.objects.all()[1]

        self.assertFalse(ppipn.flag)
        self.assertTrue(ppipn1.flag)
        self.assertEqual(ppipn1.flag_info, 'Duplicate txn_id. (test_txn_id)')

        # even if the postback is verified, it is flagged and processed as
        # invalid
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            mail.outbox[0].subject,
            'WARNING! Invalid Payment Notification received from PayPal'
        )

    @patch('paypal.standard.ipn.models.PayPalIPN._postback')
    @patch('payments.models.send_processed_payment_emails')
    def test_error_sending_emails_payment_received(
            self, mock_send_emails, mock_postback
    ):
        """
        We send a warning email with the exception if anything else goes wrong
        during the payment processing; most likely to be something wrong with
        sending the emails
        """
        mock_send_emails.side_effect = Exception('Error sending mail')
        mock_postback.return_value = b"VERIFIED"

        booking = baker.make(Booking, event__name='Workshop',
                             event__paypal_email=TEST_RECEIVER_EMAIL)
        pptrans = create_paypal_transaction(booking.user, booking)

        params = dict(IPN_POST_PARAMS)
        params.update(
            {
                'custom': b('booking {}'.format(booking.id)),
                'invoice': b(pptrans.invoice_id),
                'txn_id': 'test_txn_id'
            }
        )
        self.paypal_post(params)
        booking.refresh_from_db()

        ppipn = PayPalIPN.objects.first()
        self.assertFalse(ppipn.flag)

        # even if the postback is verified, it is flagged and processed as
        # invalid
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            mail.outbox[0].subject,
            '{} There was some problem processing payment for '
            'booking id {}'.format(
                settings.ACCOUNT_EMAIL_SUBJECT_PREFIX, booking.id
            ),
        )

        self.assertEqual(
            mail.outbox[0].body,
            'Please check your booking and paypal records for invoice # {}, '
            'paypal transaction id test_txn_id.\n\nThe exception '
            'raised was "Error sending mail"'.format(pptrans.invoice_id)
        )

    @patch('payments.models.send_mail')
    def test_error_sending_emails_payment_not_received(self, mock_send_emails):
        """
        We send a warning email with the exception if anything else goes wrong
        during the payment processing; most likely to be something wrong with
        sending the emails, so we need to check the logs
        """
        mock_send_emails.side_effect = Exception('Error sending mail')
        payment_models_logger.warning = Mock()

        booking = baker.make(Booking, event__name='Workshop',
                             event__paypal_email=TEST_RECEIVER_EMAIL)
        pptrans = create_paypal_transaction(booking.user, booking)

        params = dict(IPN_POST_PARAMS)
        params.update(
            {
                'custom': b('booking {}'.format(booking.id)),
                'invoice': b(pptrans.invoice_id),
                'txn_id': 'test_txn_id'
            }
        )

        with self.assertRaises(Exception):
            self.paypal_post(params)
            payment_models_logger.warning.assert_called_with(
                'Problem processing payment_not_received for '
                'booking {}; '
                'invoice_id {}, transaction id: test_txn_id. Exception: '
                'Error sending mail'.format(booking.id, pptrans.invoice)
            )

        booking.refresh_from_db()
        ppipn = PayPalIPN.objects.first()

        self.assertTrue(ppipn.flag)
        self.assertEqual(ppipn.flag_info, 'Invalid postback. (INVALID)')

    @patch('paypal.standard.ipn.models.PayPalIPN._postback')
    def test_paypal_notify_with_mismatched_business(self, mock_postback):
        """
        Test that error is raised if business doesn't match object's
        paypal_email. Warning mail sent to support.
        """
        mock_postback.return_value = b"VERIFIED"
        booking = baker.make(Booking, event__name='Workshop',
                             event__paypal_email=TEST_RECEIVER_EMAIL)
        pptrans = create_paypal_transaction(booking.user, booking)

        self.assertFalse(PayPalIPN.objects.exists())
        params = dict(IPN_POST_PARAMS)
        params.update(
            {
                'custom': b('booking {}'.format(booking.id)),
                'invoice': b(pptrans.invoice_id),
                'txn_id': b'test_txn_id',
                'business': b'fake@test.com'
            }
        )
        self.assertIsNone(pptrans.transaction_id)
        self.paypal_post(params)
        self.assertEqual(PayPalIPN.objects.count(), 1)
        ppipn = PayPalIPN.objects.first()
        self.assertTrue(ppipn.flag)
        self.assertEqual(
            ppipn.flag_info,
            'Invalid business email (fake@test.com)'
        )

        booking.refresh_from_db()
        self.assertFalse(booking.paid)

        # email to user, studio, and support email
        self.assertEqual(len(mail.outbox), 1)
        support_email = mail.outbox[0]
        self.assertEqual(support_email.to, [settings.SUPPORT_EMAIL])
        self.assertEqual(
            support_email.subject,
            '{} There was some problem processing payment for booking '
            'id {}'.format(settings.ACCOUNT_EMAIL_SUBJECT_PREFIX, booking.id)
        )
        self.assertIn(
            'The exception raised was "Invalid business email (fake@test.com)',
            support_email.body
        )

    @patch('paypal.standard.ipn.models.PayPalIPN._postback')
    def test_paypal_notify_with_pending_payment_status(self, mock_postback):
        """
        Test that error is raised and warning mail sent to support for a
        payment status that is not Completed or Refunded.
        """
        mock_postback.return_value = b"VERIFIED"
        booking = baker.make(Booking, event__name='Workshop',
                             event__paypal_email=TEST_RECEIVER_EMAIL)
        pptrans = create_paypal_transaction(booking.user, booking)

        self.assertFalse(PayPalIPN.objects.exists())
        params = dict(IPN_POST_PARAMS)
        params.update(
            {
                'custom': b('booking {}'.format(booking.id)),
                'invoice': b(pptrans.invoice_id),
                'txn_id': b'test_txn_id',
                'payment_status': 'Pending'
            }
        )
        self.assertIsNone(pptrans.transaction_id)
        self.paypal_post(params)
        self.assertEqual(PayPalIPN.objects.count(), 1)
        ppipn = PayPalIPN.objects.first()

        booking.refresh_from_db()
        self.assertFalse(booking.paid)

        # email to support email
        self.assertEqual(len(mail.outbox), 1)
        support_email = mail.outbox[0]
        self.assertEqual(support_email.to, [settings.SUPPORT_EMAIL])
        self.assertEqual(
            support_email.subject,
            '{} There was some problem processing payment for booking '
            'id {}'.format(settings.ACCOUNT_EMAIL_SUBJECT_PREFIX, booking.id)
        )
        self.assertIn(
            'The exception raised was "PayPal payment returned with '
            'status PENDING for booking {}; '
            'ipn obj id {} (txn id {}).  This is usually due to an '
            'unrecognised or unverified paypal email address.'.format(
                booking.id, ppipn.id, ppipn.txn_id
            ),
            support_email.body
        )

    @patch('paypal.standard.ipn.models.PayPalIPN._postback')
    def test_paypal_notify_with_unexpected_payment_status(self, mock_postback):
        """
        Test that error is raised and warning mail sent to support for a
        payment status that is not Completed or Refunded.
        """
        mock_postback.return_value = b"VERIFIED"
        booking = baker.make(Booking, event__name='Workshop',
                             event__paypal_email=TEST_RECEIVER_EMAIL)
        pptrans = create_paypal_transaction(booking.user, booking)

        self.assertFalse(PayPalIPN.objects.exists())
        params = dict(IPN_POST_PARAMS)
        params.update(
            {
                'custom': b('booking {}'.format(booking.id)),
                'invoice': b(pptrans.invoice_id),
                'txn_id': b'test_txn_id',
                'payment_status': 'Voided'
            }
        )
        self.assertIsNone(pptrans.transaction_id)
        self.paypal_post(params)
        self.assertEqual(PayPalIPN.objects.count(), 1)
        ppipn = PayPalIPN.objects.first()

        booking.refresh_from_db()
        self.assertFalse(booking.paid)

        # email to support email
        self.assertEqual(len(mail.outbox), 1)
        support_email = mail.outbox[0]
        self.assertEqual(support_email.to, [settings.SUPPORT_EMAIL])
        self.assertEqual(
            support_email.subject,
            '{} There was some problem processing payment for booking '
            'id {}'.format(settings.ACCOUNT_EMAIL_SUBJECT_PREFIX, booking.id)
        )
        self.assertIn(
            'The exception raised was "Unexpected payment status VOIDED for '
            'booking {}; ipn obj id {} (txn id {})'.format(
                booking.id, ppipn.id, ppipn.txn_id
            ),
            support_email.body
        )

    @patch('paypal.standard.ipn.models.PayPalIPN._postback')
    def test_paypal_email_check(self, mock_postback):
        """
        Test that a paypal test payment is processed properly and
        email is sent to the user and to support.
        """
        mock_postback.return_value = b"VERIFIED"
        self.assertFalse(PayPalIPN.objects.exists())
        params = dict(IPN_POST_PARAMS)
        params.update(
            {
                'custom': b('paypal_test 0 test_invoice_1 '
                            'test@test.com user@test.com'),
                'business': 'test@test.com'
            }
        )
        self.assertNotEqual(
            settings.DEFAULT_PAYPAL_EMAIL, params['receiver_email']
        )
        self.paypal_post(params)

        ipn = PayPalIPN.objects.first()
        self.assertEqual(ipn.payment_status, 'Completed')

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, ['user@test.com', settings.SUPPORT_EMAIL])
        self.assertEqual(
            email.subject,
            '{} Payment processed for test payment to PayPal email '
            'test@test.com'.format(
                settings.ACCOUNT_EMAIL_SUBJECT_PREFIX
            )
        )

    @patch('paypal.standard.ipn.models.PayPalIPN._postback')
    def test_paypal_email_check_refunded_status(self, mock_postback):
        """
        Test that a refunded paypal test payment is processed properly
        and email is sent to the user and to support.
        """
        mock_postback.return_value = b"VERIFIED"
        self.assertFalse(PayPalIPN.objects.exists())
        params = dict(IPN_POST_PARAMS)
        params.update(
            {
                'custom': b('paypal_test 0 test_invoice_1 '
                            'test@test.com user@test.com'),
                'business': 'test@test.com',
                'payment_status': 'Refunded'
            }
        )
        self.paypal_post(params)

        ipn = PayPalIPN.objects.first()
        self.assertEqual(ipn.payment_status, 'Refunded')

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, ['user@test.com', settings.SUPPORT_EMAIL])
        self.assertEqual(
            email.subject,
            '{} Payment refund processed for test payment to PayPal email '
            'test@test.com'.format(
                settings.ACCOUNT_EMAIL_SUBJECT_PREFIX
            )
        )

    @patch('paypal.standard.ipn.models.PayPalIPN._postback')
    def test_paypal_email_check_pending_status(self, mock_postback):
        """
        Test that a paypal test payment with pending status is processed
        properly and email is sent to the user and to support.
        """
        mock_postback.return_value = b"VERIFIED"
        self.assertFalse(PayPalIPN.objects.exists())
        params = dict(IPN_POST_PARAMS)
        params.update(
            {
                'custom': b('paypal_test 0 test_invoice_1 '
                            'test@test.com user@test.com'),
                'business': 'test@test.com',
                'payment_status': 'Pending',
            }
        )
        self.assertNotEqual(
            settings.DEFAULT_PAYPAL_EMAIL, params['receiver_email']
        )
        self.paypal_post(params)

        ipn = PayPalIPN.objects.first()
        self.assertEqual(ipn.payment_status, 'Pending')

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, ['user@test.com', settings.SUPPORT_EMAIL])
        self.assertEqual(
            email.subject,
            '{} Payment status PENDING for test payment to PayPal email '
            'test@test.com'.format(
                settings.ACCOUNT_EMAIL_SUBJECT_PREFIX
            )
        )

    @patch('paypal.standard.ipn.models.PayPalIPN._postback')
    def test_paypal_email_check_unexpected_status(self, mock_postback):
        """
        Test that a paypal test payment with unexpected status is processed
        properly and email is sent to the user and to support.
        """
        mock_postback.return_value = b"VERIFIED"
        self.assertFalse(PayPalIPN.objects.exists())
        params = dict(IPN_POST_PARAMS)
        params.update(
            {
                'custom': b('paypal_test 0 test_invoice_1 '
                            'test@test.com user@test.com'),
                'business': 'test@test.com',
                'payment_status': 'Voided',
            }
        )
        self.assertNotEqual(
            settings.DEFAULT_PAYPAL_EMAIL, params['receiver_email']
        )
        self.paypal_post(params)

        ipn = PayPalIPN.objects.first()
        self.assertEqual(ipn.payment_status, 'Voided')

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, ['user@test.com', settings.SUPPORT_EMAIL])

        self.assertEqual(
            email.subject,
            '{} Unexpected payment status VOIDED '
            'for test payment to PayPal email test@test.com'.format(
                settings.ACCOUNT_EMAIL_SUBJECT_PREFIX
            ),
        )

    @patch('payments.models.send_processed_test_confirmation_emails')
    @patch('paypal.standard.ipn.models.PayPalIPN._postback')
    def test_paypal_email_check_unexpected_error(
            self, mock_postback, mock_send_confirmation
    ):
        """
        Test that a paypal test payment that fails in some unexpected way
        sends email to support.
        """
        mock_postback.return_value = b"VERIFIED"
        mock_send_confirmation.side_effect = Exception('Error')
        params = dict(IPN_POST_PARAMS)

        params.update(
            {
                'custom': b('paypal_test 0 test_invoice_1 '
                            'test@test.com user@test.com'),
                'business': 'test@test.com',
            }
        )
        self.paypal_post(params)

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, [settings.SUPPORT_EMAIL])

        self.assertEqual(
            email.subject,
            '{} There was some problem processing payment for paypal_test '
            'payment to paypal email test@test.com'.format(
                settings.ACCOUNT_EMAIL_SUBJECT_PREFIX
            )
        )
        self.assertIn('The exception raised was "Error"', email.body)
