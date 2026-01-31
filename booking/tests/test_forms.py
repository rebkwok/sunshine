# -*- coding: utf-8 -*-
from django.test import TestCase
from django.utils import timezone
from model_bakery import baker

from booking.forms import BookingCreateForm, ItemVoucherForm


class BookingCreateFormTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = baker.make_recipe("booking.user")
        cls.event = baker.make_recipe("booking.future_EV")

    def test_create_form(self):
        form_data = {"event": self.event.id}
        form = BookingCreateForm(data=form_data)
        self.assertTrue(form.is_valid())


def test_item_voucher():
    data = {
        "code": "test",
        "discount": 10,
        "event_types": ["workshop"],
        "start_date": timezone.now(),
    }

    form = ItemVoucherForm(data)
    assert form.is_valid()


def test_item_voucher_code_with_spaces():
    data = {
        "code": "test code",
        "discount": 10,
        "event_types": ["workshop"],
        "start_date": timezone.now(),
    }

    form = ItemVoucherForm(data)
    assert not form.is_valid()
    assert form.errors == {"code": ["Code cannot contain spaces"]}


def test_item_voucher_no_items():
    data = {"code": "test", "discount": 10, "start_date": timezone.now()}

    form = ItemVoucherForm(data)
    assert not form.is_valid()
    assert form.non_field_errors() == [
        "Specify at least one membership type or event type that this voucher is valid for"
    ]
