from model_mommy import mommy

from django.core.urlresolvers import reverse
from django.test import TestCase

from paypal.standard.ipn.models import PayPalIPN

from entries.models import Entry


class TestViews(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.url = reverse('payments:paypal_confirm')

    def test_confirm_return(self):
        entry = mommy.make(Entry)
        resp = self.client.post(
            self.url,
            {
                'custom': 'video {}'.format(entry.id),
                'payment_status': 'paid',
                'item_name': 'Video entry fee'
            }
        )
        self.assertEquals(resp.status_code, 200)
        self.assertEquals(resp.context_data['payment_type'], 'video')
        self.assertEquals(resp.context_data['obj'], entry)

    def test_confirm_return_with_unknown_obj(self):
        resp = self.client.post(
            self.url,
            {
                'custom': 'other',
                'payment_status': 'paid',
                'item_name': 'Video entry fee'
            }
        )
        self.assertEquals(resp.status_code, 200)
        self.assertEquals(resp.context_data['obj_unknown'], True)
        self.assertIn(
            'Everything is probably fine...',
            resp.rendered_content
        )

    def test_confirm_return_with_no_custom_field(self):
        resp = self.client.post(
            self.url,
            {
                'payment_status': 'paid',
                'item_name': 'Video entry fee'
            }
        )
        self.assertEquals(resp.status_code, 200)
        self.assertEquals(resp.context_data['obj_unknown'], True)
        self.assertIn(
            'Everything is probably fine...',
            resp.rendered_content
        )

    def test_cancel_return(self):
        url = reverse('payments:paypal_cancel')
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 200)
