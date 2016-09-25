from datetime import datetime
from model_mommy import mommy

from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.utils import timezone

from entries.models import Entry
from ..models import create_entry_paypal_transaction, PaypalEntryTransaction


class TestHelpers(TestCase):

    def test_create_entry_transaction(self):
        user = mommy.make(User)
        entry = mommy.make(Entry)
        ppt = create_entry_paypal_transaction(user, entry, 'video')
        self.assertEqual(ppt.entry, entry)
        self.assertEqual(ppt.invoice_id,'{}-video-inv#001'.format(entry.entry_ref))
        # str returns invoice id
        self.assertEqual(str(ppt), ppt.invoice_id)

    def test_try_to_create_existing_entry_transaction(self):
        user = mommy.make(User)
        entry = mommy.make(Entry)
        ppt = create_entry_paypal_transaction(user, entry, 'video')
        self.assertEqual(ppt.entry, entry)
        self.assertEqual(ppt.invoice_id, '{}-video-inv#001'.format(entry.entry_ref))
        self.assertEqual(PaypalEntryTransaction.objects.count(), 1)

        duplicate_ppt = create_entry_paypal_transaction(user, entry, 'video')
        self.assertEqual(PaypalEntryTransaction.objects.count(), 1)
        self.assertEqual(ppt, duplicate_ppt)

    def test_create_existing_entry_txn_with_txn_id(self):
        """
        if the existing transaction is already associated with a paypal
        transaction_id, we do need to create a new transaction, with new
        invoice number with incremented counter
        """
        user = mommy.make(User)
        entry = mommy.make(Entry)
        ppt = create_entry_paypal_transaction(user, entry, 'video')
        self.assertEqual(ppt.entry, entry)
        self.assertEqual(ppt.invoice_id, '{}-video-inv#001'.format(entry.entry_ref))
        self.assertEqual(PaypalEntryTransaction.objects.count(), 1)

        ppt.transaction_id = "123"
        ppt.save()
        new_ppt = create_entry_paypal_transaction(user, entry, 'video')
        self.assertEqual(PaypalEntryTransaction.objects.count(), 2)
        self.assertEqual(new_ppt.invoice_id, '{}-video-inv#002'.format(entry.entry_ref))
