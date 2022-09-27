# -*- coding: utf-8 -*-
from model_bakery import baker
import pytest
from django.urls import reverse

from stripe_payments.models import Invoice


pytestmark = pytest.mark.django_db


def test_login_required(client, configured_user):
    url = reverse('booking:transactions')
    resp = client.get(url)
    assert resp.status_code == 302
    assert reverse("account_login") in resp.url
    
    client.force_login(configured_user)
    resp = client.get(url)
    assert resp.status_code == 200


def test_paid_invoices_shown(client, configured_user):
    url = reverse('booking:transactions')
    paid = baker.make(Invoice, username=configured_user.email, paid=True)
    unpaid = baker.make(Invoice, username=configured_user.email, paid=False)
    baker.make_recipe("booking.booking", user=configured_user, paid=True, invoice=paid)
    baker.make_recipe("booking.booking", user=configured_user, paid=True, invoice=unpaid)
    client.force_login(configured_user)
    resp = client.get(url)
    assert [inv.id for inv in resp.context_data['invoices']] == [paid.id]
