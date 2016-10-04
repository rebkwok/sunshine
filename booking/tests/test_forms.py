# -*- coding: utf-8 -*-

from django.test import TestCase
from model_mommy import mommy

from booking.forms import BookingCreateForm


class BookingCreateFormTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = mommy.make_recipe('booking.user')
        cls.event = mommy.make_recipe('booking.future_EV')

    def test_create_form(self):
        form_data = {'event': self.event.id}
        form = BookingCreateForm(data=form_data)
        self.assertTrue(form.is_valid())

