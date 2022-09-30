# -*- coding: utf-8 -*-
from django.conf import settings
from django.contrib.auth.models import User
from django.core import mail
from django.urls import reverse
from django.test import TestCase


class WebsitePagesTests(TestCase):

    def test_get_home_page(self):
        resp = self.client.get(reverse('website:home'))
        assert resp.status_code == 200

    def test_get_faq_page(self):
        resp = self.client.get(reverse('website:faq'))
        assert resp.status_code == 200

    def test_get_contact_page(self):
        resp = self.client.get(reverse('website:contact'))
        assert resp.status_code == 200


class ContactFormTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.url = reverse('website:contact_form')
        cls.user = User.objects.create(
            username='test', email='test@test.com', password='test'
        )

    def test_get_contact_form(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)

        # no data on session
        self.assertEqual(
            resp.context['form'].initial['subject'], 'Website Enquiry'
        )
        self.assertEqual(
            resp.context['form'].initial['first_name'], ''
        )
        self.assertEqual(
            resp.context['form'].initial['last_name'], ''
        )
        self.assertEqual(
            resp.context['form'].initial['email_address'], ''
        )
        self.assertFalse(
            resp.context['form'].initial['data_privacy_accepted']
        )
        sess = self.client.session
        sess['first_name'] = 'Donald'
        sess['last_name'] = "Duck"
        sess['email_address'] = 'dd@test.com'
        sess['data_privacy_accepted'] = True
        sess.save()

        resp = self.client.get(
            self.url, HTTP_REFERER='http://test.com/membership/'
        )

        # data on session
        self.assertEqual(
            resp.context['form'].initial['subject'], 'Website Enquiry'
        )
        self.assertEqual(
            resp.context['form'].initial['first_name'], 'Donald'
        )
        self.assertEqual(
            resp.context['form'].initial['last_name'], 'Duck'
        )
        self.assertEqual(
            resp.context['form'].initial['email_address'], 'dd@test.com'
        )
        self.assertTrue(
            resp.context['form'].initial['data_privacy_accepted']
        )

    def test_get_contact_page(self):
        resp = self.client.get(reverse('website:contact'))
        self.assertEqual(resp.status_code, 200)

        # no data on session
        self.assertEqual(
            resp.context['form'].initial['subject'], 'Website Enquiry'
        )
        self.assertEqual(
            resp.context['form'].initial['first_name'], ''
        )
        self.assertEqual(
            resp.context['form'].initial['last_name'], ''
        )
        self.assertEqual(
            resp.context['form'].initial['email_address'], ''
        )

    def test_send_contact_form(self):
        data = {
            'subject': 'General Enquiry',
            'first_name': 'Donald',
            'last_name': 'Duck',
            'email_address': 'dd@test.com',
            'message': 'Test message',
            'cc': True,
            'data_privacy_accepted': True,
        }

        resp = self.client.post(self.url, data)
        self.assertEqual(resp.status_code, 302)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [settings.DEFAULT_STUDIO_EMAIL])
        self.assertEqual(mail.outbox[0].cc, ['dd@test.com'])

    def test_send_contact_form_with_errors(self):
        data = {
            'subject': 'General Enquiry',
            'first_name': 'Donald',
            'last_name': 'Duck',
            'email_address': 'dd@test.com',
            'message': '',
            'cc': True,
            'data_privacy_accepted': True,
        }

        resp = self.client.post(self.url, data)
        self.assertFalse(resp.context['form'].is_valid())
        self.assertEqual(
            resp.context['form'].errors,
            {'message': ['This field is required.']}
        )
        self.assertEqual(len(mail.outbox), 0)
