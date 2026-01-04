# -*- coding: utf-8 -*-

from model_bakery import baker

from django.urls import reverse
from django.test import TestCase


from booking.views import EventDetailView
from booking.tests.helpers import TestSetupMixin


class BookingtagTests(TestSetupMixin, TestCase):

    @classmethod
    def setUpTestData(cls):
        super(BookingtagTests, cls).setUpTestData()
        cls.user.is_staff = True
        cls.user.save()

    def _get_response(self, user, event):
        url = reverse('booking:event_detail', args=[event.slug])
        request = self.factory.get(url)
        request.user = user
        view = EventDetailView.as_view()
        return view(request, slug=event.slug)

    def test_cancellation_format_tag_event_detail(self):
        """
        Test that cancellation period is formatted correctly
        """
        event = baker.make_recipe('booking.future_EV', cancellation_period=24)
        resp = self._get_response(self.user, event)
        resp.render()
        self.assertIn('24 hours', str(resp.content))

        event = baker.make_recipe('booking.future_EV', cancellation_period=25)
        resp = self._get_response(self.user, event)
        resp.render()
        self.assertIn('1 day and 1 hour', str(resp.content))

        event = baker.make_recipe('booking.future_EV', cancellation_period=48)
        resp = self._get_response(self.user, event)
        resp.render()
        self.assertIn('2 days', str(resp.content))

        event = baker.make_recipe('booking.future_EV', cancellation_period=619)
        resp = self._get_response(self.user, event)
        resp.render()
        self.assertIn('3 weeks, 4 days and 19 hours', str(resp.content))

        event = baker.make_recipe('booking.future_EV', cancellation_period=168)
        resp = self._get_response(self.user, event)
        resp.render()
        self.assertIn('1 week', str(resp.content))

        event = baker.make_recipe('booking.future_EV', cancellation_period=192)
        resp = self._get_response(self.user, event)
        resp.render()
        self.assertIn('1 week, 1 day and 0 hours', str(resp.content))

