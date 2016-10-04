# -*- coding: utf-8 -*-

from model_mommy import mommy

from django.contrib.auth.models import User
from django.contrib.admin.sites import AdminSite
from django.test import TestCase

from paypal.standard.ipn.models import PayPalIPN

from booking.models import Booking

from .. import admin
from ..models import PaypalBookingTransaction, create_paypal_transaction


class PaymentsAdminTests(TestCase):

    def test_paypal_admin_display(self):
        user = mommy.make(
            User, first_name='Test', last_name='User')
        booking = mommy.make(Booking, user=user)
        pptrans = create_paypal_transaction(user, booking)

        ppbooking_admin = admin.PaypalBookingTransactionAdmin(
            PaypalBookingTransaction, AdminSite()
        )
        ppbooking_query = ppbooking_admin.get_queryset(None)[0]

        self.assertEqual(
            ppbooking_admin.get_booking_id(ppbooking_query), booking.id
        )
        self.assertEqual(
            ppbooking_admin.get_user(ppbooking_query), 'Test User')

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
            mommy.make(PaypalBookingTransaction, booking__user=user)

    def test_payments_user_filter_choices(self):
        # test that user filter shows formatted choices ordered by first name

        userfilter = admin.UserFilter(
            None, {}, PaypalBookingTransaction,
            admin.PaypalBookingTransactionAdmin
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
            None, {}, PaypalBookingTransaction,
            admin.PaypalBookingTransactionAdmin
        )
        result = userfilter.queryset(
            None, PaypalBookingTransaction.objects.all()
        )
        # with no filter parameters, return all
        self.assertEqual(PaypalBookingTransaction.objects.count(), 2)
        self.assertEqual(result.count(), 2)
        self.assertEqual(
            [ppbt.id for ppbt in result],
            [ppbt.id for ppbt in PaypalBookingTransaction.objects.all()]
        )

        userfilter = admin.UserFilter(
            None, {'user': self.user.id}, PaypalBookingTransaction,
            admin.PaypalBookingTransactionAdmin
        )
        result = userfilter.queryset(
            None, PaypalBookingTransaction.objects.all()
        )
        self.assertEqual(PaypalBookingTransaction.objects.count(), 2)
        self.assertEqual(result.count(), 1)
        self.assertEqual(
            result[0],
            PaypalBookingTransaction.objects.get(booking__user=self.user)
        )
