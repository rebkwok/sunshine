from model_mommy import mommy
from django.test import TestCase

from entries.models import Entry
from entries.views import get_paypal_dict

from ..forms import PayPalPaymentsListForm
from ..models import create_entry_paypal_transaction


class PayPalFormTests(TestCase):

    def test_PayPalPaymentsListForm_renders_buy_it_now_button(self):
        entry = mommy.make(Entry)
        pptrans = create_entry_paypal_transaction(entry.user, entry, 'video')
        form = PayPalPaymentsListForm(
            initial=get_paypal_dict(
                        'http://example.com',
                        10,
                        'Video submission fee',
                        pptrans.invoice_id,
                        'video {}'.format(entry.id),
                    )
        )
        self.assertIn('Paypal', form.render())

