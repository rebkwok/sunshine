# -*- coding: utf-8 -*-

from model_mommy import mommy

from django.contrib.auth.models import User
from django.contrib.admin.sites import AdminSite
from django.test import TestCase

from paypal.standard.ipn.models import PayPalIPN

from entries.models import Entry

from .. import admin
from ..models import PaypalEntryTransaction, create_entry_paypal_transaction


class PaymentsAdminTests(TestCase):

    def test_paypal_admin_display(self):
        user = mommy.make(
            User, first_name='Test', last_name='User')
        entry = mommy.make(Entry, user=user)
        pptrans = create_entry_paypal_transaction(user, entry, 'video')

        ppentry_admin = admin.PaypalEntryTransactionAdmin(
            PaypalEntryTransaction, AdminSite()
        )
        ppentry_query = ppentry_admin.get_queryset(None)[0]

        self.assertEqual(
            ppentry_admin.get_entry_id(ppentry_query), entry.id
        )
        self.assertEqual(
            ppentry_admin.get_user(ppentry_query), 'Test User')

    def test_paypaladmin_display(self):
        mommy.make(PayPalIPN, first_name='Mickey', last_name='Mouse')
        paypal_admin = admin.PayPalAdmin(PayPalIPN, AdminSite())
        query = paypal_admin.get_queryset(None)[0]
        self.assertEqual(paypal_admin.buyer(query), 'Mickey Mouse')


class PaymentsAdminFiltersTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = mommy.make(
            User, first_name="Foo", last_name="Bar", username="foob"
        )
        cls.user1 = mommy.make(
            User, first_name="Donald", last_name="Duck", username="dd"
        )
        for user in User.objects.all():
            mommy.make(PaypalEntryTransaction, entry__user=user)

    def test_payments_user_filter_choices(self):
        # test that user filter shows formatted choices ordered by first name

        userfilter = admin.UserFilter(
            None, {}, PaypalEntryTransaction,
            admin.PaypalEntryTransactionAdmin
        )

        self.assertEqual(
            userfilter.lookup_choices,
            [
                (self.user1.id, 'Donald Duck (dd)'),
                (self.user.id, 'Foo Bar (foob)')
            ]
        )

    def test_paypal_booking_user_filter(self):

        userfilter = admin.UserFilter(
            None, {}, PaypalEntryTransaction, admin.PaypalEntryTransactionAdmin
        )
        result = userfilter.queryset(
            None, PaypalEntryTransaction.objects.all()
        )
        # with no filter parameters, return all
        self.assertEqual(PaypalEntryTransaction.objects.count(), 2)
        self.assertEqual(result.count(), 2)
        self.assertEqual(
            [ppbt.id for ppbt in result],
            [ppbt.id for ppbt in PaypalEntryTransaction.objects.all()]
        )

        userfilter = admin.UserFilter(
            None, {'user': self.user.id}, PaypalEntryTransaction,
            admin.PaypalEntryTransactionAdmin
        )
        result = userfilter.queryset(
            None, PaypalEntryTransaction.objects.all()
        )
        self.assertEqual(PaypalEntryTransaction.objects.count(), 2)
        self.assertEqual(result.count(), 1)
        self.assertEqual(
            result[0], PaypalEntryTransaction.objects.get(entry__user=self.user)
        )
