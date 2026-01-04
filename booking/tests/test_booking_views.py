# -*- coding: utf-8 -*-
from model_bakery import baker

from django.urls import reverse
from django.test import TestCase

from accounts.models import DataPrivacyPolicy


from booking.models import Booking, WaitingListUser
from booking.views import BookingHistoryListView
from booking.tests.helpers import TestSetupMixin



class BookingListViewTests(TestSetupMixin, TestCase):

    @classmethod
    def setUpTestData(cls):
        super(BookingListViewTests, cls).setUpTestData()
        cls.regular_sessions = baker.make_recipe('booking.future_PC', _quantity=3)
        cls.events = baker.make_recipe('booking.future_EV', _quantity=2)
        baker.make_recipe('booking.past_booking', user=cls.user)
        cls.url = reverse('booking:bookings')

    def setUp(self):
        super(BookingListViewTests, self).setUp()
        self.client.login(username=self.user.username, password='test')
        self.regular_sessions_bookings = [
            baker.make_recipe('booking.booking', user=self.user, event=event) for event in self.regular_sessions
        ]
        self.event_bookings = [
            baker.make_recipe('booking.booking', user=self.user, event=event) for event in self.events
        ]

    def test_login_required(self):
        """
        test that page redirects if there is no user logged in
        """
        self.client.logout()
        resp = self.client.get(self.url)
        assert resp.status_code == 302

    def test_booking_list(self):
        """
        Test that only future bookings are listed)
        """
        resp = self.client.get(self.url)
        assert Booking.objects.all().count() == 6
        assert resp.status_code == 200
        assert resp.context_data['bookings'].count() == 5

    def test_data_policy_agreement_required(self):
        baker.make(DataPrivacyPolicy)
        resp = self.client.get(self.url)
        assert resp.status_code == 302
        assert resp.url == reverse('accounts:data_privacy_review') + '?next={}'.format(self.url)

    def test_booking_list_by_user(self):
        """
        Test that only bookings for this user are listed
        """
        another_user = baker.make_recipe('booking.user')
        baker.make_recipe(
            'booking.booking', user=another_user, event=self.regular_sessions[0]
        )
        # check there are now 7 bookings
        assert Booking.objects.all().count() == 7
        resp = self.client.get(self.url)
        # event listing should still only show this user's future bookings
        assert resp.context_data['bookings'].count() == 5

    def test_cancelled_booking_shown_in_booking_list(self):
        """
        Test that all future bookings for this user are listed
        """
        ev = baker.make_recipe('booking.future_PC', name="future event")
        baker.make_recipe(
            'booking.booking', user=self.user, event=ev,
            status='CANCELLED'
        )
        # check there are now 7 bookings (3 future, 1 past, 2 workshops,  1 cancelled)
        assert Booking.objects.all().count() == 7
        resp = self.client.get(self.url)

        # booking listing should show this user's future bookings,
        # including the cancelled one
        assert resp.context_data['bookings'].count() == 6

    def test_cancelled_bookings_on_waiting_list(self):
        ev = baker.make_recipe('booking.future_PC', name="future event")
        booking = baker.make_recipe(
            'booking.booking', user=self.user, event=ev,
            status='CANCELLED'
        )
        baker.make(WaitingListUser, user=self.user, event=ev)
        resp = self.client.get(self.url)
        assert resp.context_data['on_waiting_list_booking_ids_list'] == [booking.id]

    def test_outstanding_fees_shows_banner(self):
        booking = self.regular_sessions_bookings[0]
        booking.cancellation_fee_incurred = True
        booking.save()
        resp = self.client.get(self.url)
        assert "Your account is locked for booking due to outstanding fees" in resp.rendered_content

    def test_buttons_disabled_if_user_has_outstanding_fees(self):
        booking = self.regular_sessions_bookings[0]
        booking.cancellation_fee_incurred = True
        booking.status = "CANCELLED"
        booking.save()

        # full event - join waiting list will be disabled
        full_event = baker.make_recipe('booking.future_PC', max_participants=1)
        baker.make_recipe('booking.booking', event=full_event)
        baker.make_recipe('booking.booking', event=full_event, user=self.user, status="CANCELLED")

        resp = self.client.get(self.url)
        assert 'id="book_button_disabled"' in resp.rendered_content  # for the cancelled booking
        assert 'id="join_waiting_list_button_disabled"' in resp.rendered_content

    def test_event_booking_buttons_disabled_if_user_has_outstanding_fees(self):
        booking = self.event_bookings[0]
        booking.cancellation_fee_incurred = True
        booking.status = "CANCELLED"
        booking.save()

        # full event - join waiting list will be disabled
        full_event = baker.make_recipe('booking.future_EV', max_participants=1)
        baker.make_recipe('booking.booking', event=full_event)
        baker.make_recipe('booking.booking', event=full_event, user=self.user, status="CANCELLED")

        resp = self.client.get(self.url + '?type=workshop')
        assert 'id="book_button_disabled"' in resp.rendered_content  # for the cancelled booking
        assert 'id="join_waiting_list_button_disabled"' in resp.rendered_content


class BookingHistoryListViewTests(TestSetupMixin, TestCase):

    @classmethod
    def setUpTestData(cls):
        super(BookingHistoryListViewTests, cls).setUpTestData()
        event = baker.make_recipe('booking.future_PC')
        cls.booking = baker.make_recipe(
            'booking.booking', user=cls.user, event=event
        )
        cls.past_booking = baker.make_recipe(
            'booking.past_booking', user=cls.user
        )

    def _get_response(self, user):
        url = reverse('booking:booking_history')
        request = self.factory.get(url)
        request.user = user
        view = BookingHistoryListView.as_view()
        return view(request)

    def test_login_required(self):
        """
        test that page redirects if there is no user logged in
        """
        url = reverse('booking:booking_history')
        resp = self.client.get(url)
        assert resp.status_code == 302

    def test_booking_history_list(self):
        """
        Test that only past bookings are listed)
        """
        resp = self._get_response(self.user)

        assert Booking.objects.all().count() == 2
        assert resp.status_code == 200
        assert resp.context_data['bookings'].count() == 1

    def test_booking_history_list_by_user(self):
        """
        Test that only past booking for this user are listed
        """
        another_user = baker.make_recipe('booking.user')
        baker.make_recipe(
            'booking.booking', user=another_user, event=self.past_booking.event
        )
        # check there are now 3 bookings
        assert Booking.objects.all().count() == 3
        resp = self._get_response(self.user)

        #  listing should still only show this user's past bookings
        assert resp.context_data['bookings'].count() == 1
