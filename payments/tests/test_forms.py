from model_bakery import baker
from django.test import TestCase

from booking.views.booking_views import get_paypal_dict

from ..forms import PayPalPaymentsListForm, PayPalPaymentsUpdateForm
from ..models import create_paypal_transaction


class PayPalFormTests(TestCase):

    def test_PayPalPaymentsListForm_renders_buy_it_now_button(self):
        booking = baker.make_recipe('booking.booking')
        pptrans = create_paypal_transaction(booking.user, booking)
        form = PayPalPaymentsListForm(
            initial=get_paypal_dict(
                        'http://example.com',
                        booking.event.cost,
                        booking.event,
                        pptrans.invoice_id,
                        'booking {}'.format(booking.id)
                    )
        )
        self.assertIn('Buy it Now', form.render())

    def test_PayPalPaymentsUpdateForm_renders_buy_it_now_button(self):
        booking = baker.make_recipe('booking.booking')
        pptrans = create_paypal_transaction(booking.user, booking)
        form = PayPalPaymentsUpdateForm(
            initial=get_paypal_dict(
                        'http://example.com',
                        booking.event.cost,
                        booking.event,
                        pptrans.invoice_id,
                        'booking {}'.format(booking.id)
                    )
        )
        self.assertIn('Buy it Now', form.render())