# -*- coding: utf-8 -*-

from model_mommy import mommy

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test import TestCase, RequestFactory, override_settings

from booking.models import Event, Booking
from booking.views import EventListView, EventDetailView
from booking.tests.helpers import TestSetupMixin, format_content


class EventListViewTests(TestSetupMixin, TestCase):

    @classmethod
    def setUpTestData(cls):
        super(EventListViewTests, cls).setUpTestData()
        mommy.make_recipe('booking.future_EV', _quantity=3)

    def _get_response(self, user):
        url = reverse('booking:events')
        request = self.factory.get(url)
        request.user = user
        view = EventListView.as_view()
        return view(request)

    def test_event_list(self):
        """
        Test that all events are listed (workshops and other events)
        """
        url = reverse('booking:events')
        resp = self.client.get(url)

        self.assertEquals(Event.objects.all().count(), 3)
        self.assertEquals(resp.status_code, 200)
        self.assertEquals(resp.context['events'].count(), 3)

    def test_event_list_past_event(self):
        """
        Test that past events is not listed
        """
        mommy.make_recipe('booking.past_event')
        # check there are now 4 events
        self.assertEquals(Event.objects.all().count(), 4)
        url = reverse('booking:events')
        resp = self.client.get(url)

        # event listing should still only show future events
        self.assertEquals(resp.context['events'].count(), 3)

    def test_event_list_with_anonymous_user(self):
        """
        Test that no booked_events in context
        """
        url = reverse('booking:events')
        resp = self.client.get(url)

        # event listing should still only show future events
        self.assertFalse('booked_events' in resp.context)

    def test_all_events_shown_for_staff_user(self):
        hidden_event = Event.objects.all()[0]
        hidden_event.show_on_site = False
        hidden_event.save()

        resp = self.client.get(reverse('booking:events'))
        self.assertEqual(len(resp.context_data['events']), 2)

        self.user.is_staff = True
        self.user.save()
        self.client.login(username=self.user.username, password='test')
        resp = self.client.get(reverse('booking:events'))
        self.assertEqual(len(resp.context_data['events']), 3)

    def test_event_list_with_logged_in_user(self):
        """
        Test that booked_events in context
        """
        resp = self._get_response(self.user)
        self.assertTrue('booked_events' in resp.context_data)

    def test_event_list_with_booked_events(self):
        """
        test that booked events are shown on listing
        """
        resp = self._get_response(self.user)
        # check there are no booked events yet
        self.assertEquals(len(resp.context_data['booked_events']), 0)

        # create a booking for this user
        booked_event = Event.objects.all()[0]
        mommy.make_recipe('booking.booking', user=self.user, event=booked_event)
        resp = self._get_response(self.user)
        booked_events = [event for event in resp.context_data['booked_events']]
        self.assertEquals(len(booked_events), 1)
        self.assertTrue(booked_event.id in booked_events)

    def test_event_list_shows_only_current_user_bookings(self):
        """
        Test that only user's booked events are shown as booked
        """
        events = Event.objects.all()
        event1 = events[0]
        event2 = events[1]

        resp = self._get_response(self.user)
        # check there are no booked events yet
        self.assertEquals(len(resp.context_data['booked_events']), 0)

        # create booking for this user
        mommy.make_recipe('booking.booking', user=self.user, event=event1)
        # create booking for another user
        user1 = mommy.make_recipe('booking.user')
        mommy.make_recipe('booking.booking', user=user1, event=event2)

        # check only event1 shows in the booked events
        resp = self._get_response(self.user)
        booked_events = [event for event in resp.context_data['booked_events']]
        self.assertEquals(Booking.objects.all().count(), 2)
        self.assertEquals(len(booked_events), 1)
        self.assertTrue(event1.id in booked_events)


class EventDetailViewTests(TestSetupMixin, TestCase):

    @classmethod
    def setUpTestData(cls):
        super(EventDetailViewTests, cls).setUpTestData()
        mommy.make_recipe('booking.future_EV', _quantity=3)

    def setUp(self):
        self.event = mommy.make_recipe('booking.future_EV')

    def _get_response(self, user, event):
        url = reverse('booking:event_detail', args=[event.slug])
        request = self.factory.get(url)
        request.user = user
        view = EventDetailView.as_view()
        return view(request, slug=event.slug)

    def test_not_logged_in(self):
        """
        test that page loads if not logged in.
        No booking or waiting list buttons shown.
        """
        resp = self.client.get(
            reverse('booking:event_detail', args=[self.event.slug])
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEquals(resp.context_data['event_type'], 'workshop')
        self.assertEquals(
            resp.context_data['booking_info_text'], 'Please log in to book.'
        )
        self.assertNotIn('book_button', resp.rendered_content)
        self.assertNotIn('join_waiting_list_button', resp.rendered_content)
        self.assertNotIn('leave_waiting_list_button', resp.rendered_content)

    def test_not_logged_in_full_event(self):
        """
        test that page loads if not logged in.
        No booking or waiting list buttons shown.
        """
        self.event.max_participants = 3
        self.event.save()
        mommy.make(Booking, event=self.event, _quantity=3)
        resp = self.client.get(
            reverse('booking:event_detail', args=[self.event.slug])
        )

        self.assertEquals(
            resp.context_data['booking_info_text'],
            'This workshop is now full.  Please log in to join the '
            'waiting list.'
        )
        self.assertNotIn('book_button', resp.rendered_content)
        self.assertNotIn('join_waiting_list_button', resp.rendered_content)
        self.assertNotIn('leave_waiting_list_button', resp.rendered_content)

    def test_with_logged_in_user(self):
        """
        test that page loads if there user is available
        """
        resp = self._get_response(self.user, self.event)
        self.assertEqual(resp.status_code, 200)
        self.assertEquals(resp.context_data['event_type'], 'workshop')

    def test_show_on_site(self):
        # can get if show on site
        url = reverse('booking:event_detail', args=[self.event.slug])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

        # can't get if not show on site
        self.event.show_on_site = False
        self.event.save()
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 404)

        # still can't get if not show on site and logged in as normal user
        self.client.login(username=self.user.username, password='test')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 404)

        # can get if logged in as staff user
        self.user.is_staff = True
        self.user.save()
        self.client.login(username=self.user.username, password='test')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(
            'PREVIEW ONLY: THIS PAGE IS NOT VISIBLE TO NON-STAFF USERS',
            resp.rendered_content
        )


    def test_with_booked_event(self):
        """
        Test that booked event is shown as booked
        """
        #create a booking for this event and user
        mommy.make_recipe('booking.booking', user=self.user, event=self.event)
        resp = self._get_response(self.user, self.event)
        self.assertTrue(resp.context_data['booked'])
        self.assertEquals(resp.context_data['booking_info_text'],
                          'You have booked for this workshop.')

    def test_with_booked_event_for_different_user(self):
        """
        Test that the event is not shown as booked if the current user has
        not booked it
        """
        user1 = mommy.make_recipe('booking.user')
        #create a booking for this event and a different user
        mommy.make_recipe('booking.booking', user=user1, event=self.event)

        resp = self._get_response(self.user, self.event)
        self.assertFalse('booked' in resp.context_data)
        self.assertEquals(resp.context_data['booking_info_text'], '')

    def test_cancellation_information_displayed_cancellation_period(self):
        """
        If booking cancellation allowed, show cancellation period if there
        is one
        If booking cancellation not allowed, show nonrefundable message
        """
        self.event.cost = 10
        self.event.save()

        self.assertTrue(self.event.allow_booking_cancellation)
        self.assertEqual(self.event.cancellation_period, 24)

        resp = self._get_response(self.user, self.event)

        # show cancellation period and due date text
        self.assertIn(
            'Cancellation is allowed up to 24 hours prior to the workshop',
            format_content(resp.rendered_content)
        )

    def test_cancellation_information_displayed_cancellation_not_allowed(self):
        """
        For not cancelled future events, show cancellation info
        If booking cancellation allowed, show cancellation period if there
        is one
        No payment_due_date or payment_time_allowed --> show due date with
        cancellation period
        If booking cancellation not allowed, show nonrefundable message
        """
        self.event.cost = 10
        self.event.allow_booking_cancellation = False
        self.event.save()

        self.assertEqual(self.event.cancellation_period, 24)

        resp = self._get_response(self.user, self.event)

        # don't show cancellation period and due date text
        self.assertNotIn(
            'Cancellation is allowed up to 24 hours prior to the workshop ',
            format_content(resp.rendered_content)
        )
        self.assertIn(
            'Bookings are final and non-refundable; if you cancel your '
            'booking you will not be eligible for any refund or credit.',
            format_content(resp.rendered_content)
        )

    def test_past_event(self):
        past_event = mommy.make_recipe('booking.past_event')
        resp = self._get_response(self.user, past_event)
        self.assertTrue(resp.context_data['past'])
        self.assertNotIn('book_button', resp.rendered_content)
        self.assertNotIn('join_waiting_list_button', resp.rendered_content)
        self.assertNotIn('leave_waiting_list_button', resp.rendered_content)

    def test_cancelled_booking(self):
        # create a cancelled booking for this event and user
        mommy.make_recipe(
            'booking.booking', user=self.user, event=self.event,
            status='CANCELLED'
        )
        resp = self._get_response(self.user, self.event)
        self.assertTrue(resp.context_data['cancelled'])
        self.assertEquals(resp.context_data['booking_info_text'], '')
        self.assertEquals(
            resp.context_data['booking_info_text_cancelled'],
            'You have previously booked for this workshop and your booking '
            'has been cancelled.'
        )

    def test_no_show_booking(self):
        """
        No show booking displays as cancelled to user
        """
        # create a no_show booking for this event and user
        mommy.make_recipe(
            'booking.booking', user=self.user, event=self.event,
            status='OPEN', no_show=True
        )
        resp = self._get_response(self.user, self.event)
        self.assertTrue(resp.context_data['cancelled'])
        self.assertEquals(resp.context_data['booking_info_text'], '')
        self.assertEquals(
            resp.context_data['booking_info_text_cancelled'],
            'You have previously booked for this workshop and your booking '
            'has been cancelled.'
        )