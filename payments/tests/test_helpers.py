from model_mommy import mommy

from django.contrib.auth.models import User
from django.test import TestCase

from booking.models import Booking
from ..models import create_paypal_transaction, PaypalBookingTransaction


class TestHelpers(TestCase):

    def test_create_entry_transaction(self):
        user = mommy.make(User)
        booking = mommy.make(Booking)
        ppt = create_paypal_transaction(user, booking)
        self.assertEqual(ppt.booking, booking)
        self.assertEqual(
            ppt.invoice_id, '{}-inv#001'.format(booking.booking_reference)
        )
        # str returns invoice id
        self.assertEqual(str(ppt), ppt.invoice_id)

    def test_try_to_create_existing_entry_transaction(self):
        user = mommy.make(User)
        booking = mommy.make(Booking)
        ppt = create_paypal_transaction(user, booking)
        self.assertEqual(ppt.booking, booking)
        self.assertEqual(
            ppt.invoice_id, '{}-inv#001'.format(booking.booking_reference)
        )
        self.assertEqual(PaypalBookingTransaction.objects.count(), 1)

        duplicate_ppt = create_paypal_transaction(user, booking)
        self.assertEqual(PaypalBookingTransaction.objects.count(), 1)
        self.assertEqual(ppt, duplicate_ppt)

    def test_create_existing_entry_txn_with_txn_id(self):
        """
        if the existing transaction is already associated with a paypal
        transaction_id, we do need to create a new transaction, with new
        invoice number with incremented counter
        """
        user = mommy.make(User)
        booking = mommy.make(Booking)
        ppt = create_paypal_transaction(user, booking)
        self.assertEqual(ppt.booking, booking)
        self.assertEqual(
            ppt.invoice_id, '{}-inv#001'.format(booking.booking_reference)
        )
        self.assertEqual(PaypalBookingTransaction.objects.count(), 1)

        ppt.transaction_id = "123"
        ppt.save()
        new_ppt = create_paypal_transaction(user, booking)
        self.assertEqual(PaypalBookingTransaction.objects.count(), 2)
        self.assertEqual(
            new_ppt.invoice_id, '{}-inv#002'.format(booking.booking_reference)
        )
