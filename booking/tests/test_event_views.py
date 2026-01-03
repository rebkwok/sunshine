# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from datetime import timezone as dt_timezone

from unittest.mock import patch

from model_bakery import baker

from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone
from django.test import TestCase

from booking.models import Event, Booking, WaitingListUser, Workshop 
from booking.tests.helpers import TestSetupMixin, format_content, make_online_disclaimer


class EventListViewTests(TestSetupMixin, TestCase):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        make_online_disclaimer(user=cls.user)
        venue = baker.make_recipe('booking.venue', location__name="venue", order=100)
        cls.events = baker.make_recipe('booking.future_EV', venue=venue, _quantity=3)
        cls.reg_class1 = baker.make_recipe('booking.future_PC', name='Class 1', venue=venue)
        cls.reg_class2 = baker.make_recipe('booking.future_PC', name='Class 2', venue=venue)
        cls.regular_classes = [cls.reg_class1, cls.reg_class2]
        cls.classes_url = reverse("booking:regular_session_list")
        cls.workshops_url = reverse("booking:workshop_list")
        cls.private_url = reverse("booking:private_list")

    def setUp(self):
        self.client.login(username=self.user.username, password='test')

    def test_event_list(self):
        """
        Test that all events are listed (workshops and other events)
        """
        resp = self.client.get(self.workshops_url)

        assert Event.objects.all().count() == 5
        assert resp.status_code == 200
        assert resp.context['events'].count() == 3

        resp = self.client.get(self.classes_url)
        assert resp.status_code == 200
        assert resp.context['events'].count() == 2

    def test_private_list_with_name(self):
        url = self.private_url
        resp = self.client.get(url)
        assert len(resp.context_data['events']) == 0
        assert resp.context_data['event_type'] == "private"

    def test_event_list_pagination(self):
        baker.make_recipe('booking.future_EV', venue__location__name="loc1", venue__order=200, _quantity=25)
        assert Workshop.objects.count() == 28

        # default (unused) paginator
        resp = self.client.get(self.workshops_url)
        assert resp.context_data["page_obj"].paginator.num_pages == 2
        assert resp.context_data["page_obj"].number == 1
        assert len(resp.context_data["events"]) == 20

        resp = self.client.get(self.workshops_url + "?page=2")
        assert len(resp.context_data["events"]) == 8
        assert resp.context_data["page_obj"].number == 2

        # bad page, returns first page
        resp = self.client.get(self.workshops_url  + "?page=3")
        assert len(resp.context_data["events"]) == 20
        assert resp.context_data["page_obj"].number == 1

        # location paginators
        # tab1 has 3 items, always returns p1
        resp = self.client.get(self.workshops_url + "?page=1&tab=1")
        venue_paginator = resp.context_data["location_events"][1]["queryset"]
        assert venue_paginator.paginator.count == 3
        assert venue_paginator.number == 1

        loc1_paginator = resp.context_data["location_events"][2]["queryset"]
        assert len(loc1_paginator.object_list) == 20
        assert loc1_paginator.paginator.count == 25
        assert loc1_paginator.number == 1

        resp = self.client.get(self.workshops_url + "?page=2&tab=1")
        venue_paginator = resp.context_data["location_events"][1]["queryset"]
        assert venue_paginator.paginator.count == 3
        assert venue_paginator.number == 1

        loc1_paginator = resp.context_data["location_events"][2]["queryset"]
        assert len(loc1_paginator.object_list) == 20
        assert loc1_paginator.paginator.count == 25
        assert loc1_paginator.number == 1

        # tab2 has 25 items
        resp = self.client.get(self.workshops_url + "?page=2&tab=2")
        venue_paginator = resp.context_data["location_events"][1]["queryset"]
        assert venue_paginator.paginator.count == 3
        assert venue_paginator.number == 1

        loc1_paginator = resp.context_data["location_events"][2]["queryset"]
        assert len(loc1_paginator.object_list) == 5
        assert loc1_paginator.paginator.count == 25
        assert loc1_paginator.number == 2

        # page out of range, returns last page
        resp = self.client.get(self.workshops_url + "?page=10&tab=2")
        loc1_paginator = resp.context_data["location_events"][2]["queryset"]
        assert len(loc1_paginator.object_list) == 5
        assert loc1_paginator.paginator.count == 25
        assert loc1_paginator.number == 2

        # page negative, returns last page
        resp = self.client.get(self.workshops_url + "?page=-10&tab=2")
        loc1_paginator = resp.context_data["location_events"][2]["queryset"]
        assert len(loc1_paginator.object_list) == 5
        assert loc1_paginator.paginator.count == 25
        assert loc1_paginator.number == 2

        # page not a number, returns first page
        resp = self.client.get(self.workshops_url + "?page=foo0&tab=2")
        loc1_paginator = resp.context_data["location_events"][2]["queryset"]
        assert len(loc1_paginator.object_list) == 20
        assert loc1_paginator.paginator.count == 25
        assert loc1_paginator.number == 1

        # tab not a number, returns first tab
        resp = self.client.get(self.workshops_url + "?page=2&tab=foo")
        assert resp.context_data["tab"] == 0

    def test_event_list_past_event(self):
        """
        Test that past events is not listed
        """
        baker.make_recipe('booking.past_event')
        # check there are now 4 events
        assert Event.objects.all().count() == 6
        url = self.workshops_url 
        resp = self.client.get(url)

        # event listing should still only show future events
        assert resp.context['events'].count() == 3

    def test_event_list_with_anonymous_user(self):
        """
        Test that no booked_events in context
        """
        self.client.logout()
        resp = self.client.get(self.workshops_url)

        # event listing should still only show future events
        assert 'booked_events' not in resp.context

    def test_all_events_shown_for_staff_user(self):
        hidden_event = Event.objects.all()[0]
        hidden_event.show_on_site = False
        hidden_event.save()

        resp = self.client.get(self.workshops_url)
        assert len(resp.context_data['events']) == 2

        self.user.is_staff = True
        self.user.save()
        
        resp = self.client.get(self.workshops_url)
        assert len(resp.context_data['events']) == 3

    def test_event_list_with_logged_in_user(self):
        """
        Test that booked_events in context
        """
        booking = baker.make_recipe('booking.booking', user=self.user, event=self.regular_classes[0])
        resp = self.client.get(self.classes_url)
        assert 'booked_events' in resp.context_data
        assert resp.context_data['booked_events'][0] == [booking.event.id][0]

    def test_event_list_show_warning(self):
        """
        Test that all events are listed (workshops and other events)
        """
        event = baker.make_recipe(
            'booking.future_EV', allow_booking_cancellation=False, cancellation_fee=0
        )
        resp = self.client.get(self.workshops_url)
        assert resp.status_code == 200
        assert resp.context['events'].count() == 4
        assert 'data-show_warning="1"' not in resp.rendered_content

        event.cancellation_fee = 1
        event.save()
        resp = self.client.get(self.workshops_url)
        assert 'data-show_warning="1"' in resp.rendered_content

    def test_event_list_with_booked_events(self):
        """
        test that booked events are shown on listing
        """
        resp = self.client.get(self.workshops_url)
        # check there are no booked events yet
        assert len(resp.context_data['booked_events']) == 0

        # create a booking for this user
        booked_event = Event.objects.all()[0]
        baker.make_recipe('booking.booking', user=self.user, event=booked_event)
        resp = self.client.get(self.workshops_url)
        booked_events = [event for event in resp.context_data['booked_events']]
        assert len(booked_events) == 1
        assert booked_event.id in booked_events

    def test_event_list_shows_only_current_user_bookings(self):
        """
        Test that only user's booked events are shown as booked
        """
        events = Event.objects.all()
        event1 = events[0]
        event2 = events[1]

        resp = self.client.get(self.workshops_url)
        # check there are no booked events yet
        assert len(resp.context_data['booked_events']) == 0

        # create booking for this user
        baker.make_recipe('booking.booking', user=self.user, event=event1)
        # create booking for another user
        user1 = baker.make_recipe('booking.user')
        baker.make_recipe('booking.booking', user=user1, event=event2)

        # check only event1 shows in the booked events
        resp = self.client.get(self.workshops_url)
        booked_events = [event for event in resp.context_data['booked_events']]
        assert Booking.objects.all().count() == 2
        assert len(booked_events) == 1
        assert event1.id in booked_events

    def test_event_list_with_name(self):
        url = self.classes_url + '?name=Class 1'
        resp = self.client.get(url)
        assert len(resp.context_data['events']) == 1
        assert resp.context_data['events'][0] == self.reg_class1

    def test_event_list_with_name_and_level(self):
        url = self.classes_url + '?name=Class 1&level=Level 1'
        resp = self.client.get(url)
        assert len(resp.context_data['events']) == 0

        event = baker.make_recipe('booking.future_PC', name='Class 1 (Level 1)')
        resp = self.client.get(url)
        assert len(resp.context_data['events']) == 1
        assert resp.context_data['events'][0] == event

    def test_event_list_with_tab(self):
        assert Event.objects.filter(event_type="regular_session").count() == 2
        baker.make_recipe('booking.future_PC', venue__location__name="loc1", venue__order=200, _quantity=10)
        baker.make_recipe('booking.future_PC', venue__location__name="loc2", venue__order=300, _quantity=15)
        assert Event.objects.filter(event_type="regular_session").count() == 27
        resp = self.client.get(self.classes_url)

        # paginated at 20
        assert len(resp.context_data['events']) == 20

        # tab 0 by default
        assert resp.context_data['tab'] == 0

        # paginated locations
        location_events = resp.context_data["location_events"]
        assert len(location_events) == 4  # all, venue, loc1, loc2 
        # all locations, paginated at 20
        assert len(location_events[0]["queryset"]) == 20
        assert len(location_events[1]["queryset"]) == 2
        assert len(location_events[2]["queryset"]) == 10
        assert len(location_events[3]["queryset"]) == 15
        

       

    @patch('booking.views.event_views.timezone.now')
    def test_event_list_with_name_day_and_time(self, mock_now):
        mock_now.return_value = datetime(2019, 1, 1, 18, 0, tzinfo=dt_timezone.utc)
        self.reg_class1.date = datetime(2019, 1, 23, 18, 0, tzinfo=dt_timezone.utc)  # Wed
        self.reg_class1.save()
        self.reg_class2.date = datetime(2019, 1, 24, 18, 0, tzinfo=dt_timezone.utc)  # Thurs
        self.reg_class2.save()
        reg_class3 = baker.make_recipe(
            'booking.future_PC', name='Class 1', date=datetime(2019, 1, 30, 18, 0, tzinfo=dt_timezone.utc)
        )  # Wed

        url = self.classes_url + '?name=Class 1&day=03WE&time=18:00'
        resp = self.client.get(url)
        assert len(resp.context_data['events']) == 2
        assert [ev.id for ev in resp.context_data['events']] == [self.reg_class1.id, reg_class3.id]

    @patch('booking.views.event_views.timezone.now')
    def test_event_list_with_day_and_time_errors(self, mock_now):
        mock_now.return_value = datetime(2019, 1, 1, 18, 0, tzinfo=dt_timezone.utc)
        self.reg_class1.date = datetime(2019, 1, 23, 18, 0, tzinfo=dt_timezone.utc)  # Wed
        self.reg_class1.save()
        self.reg_class2.date = datetime(2019, 1, 24, 18, 0, tzinfo=dt_timezone.utc)  # Thurs
        self.reg_class2.save()
        reg_class3 = baker.make_recipe(
            'booking.future_PC', name='Class 1', date=datetime(2019, 1, 31, 20, 0, tzinfo=dt_timezone.utc)
        )  # Wed, diff day/time, same name

        # misformatted time is ignored, just returns by name
        url = self.classes_url + '?name=Class 1&day=03WE&time=1800'
        resp = self.client.get(url)
        assert len(resp.context_data['events']) == 2
        assert [ev.id for ev in resp.context_data['events']] == [self.reg_class1.id, reg_class3.id]

    @patch('booking.views.event_views.timezone.now')
    def test_event_list_with_day_and_time_including_daylight_savings(self, mock_now):
        mock_now.return_value = datetime(2019, 1, 1, 18, 0, tzinfo=dt_timezone.utc)
        self.reg_class1.date = datetime(2019, 1, 23, 18, 0, tzinfo=dt_timezone.utc)  # Wed
        self.reg_class1.save()
        self.reg_class2.date = datetime(2019, 1, 24, 18, 0, tzinfo=dt_timezone.utc)  # Thurs
        self.reg_class2.save()
        reg_class3 = baker.make_recipe(
            'booking.future_PC', name='Class 1', date=datetime(2019, 8, 14, 19, 0, tzinfo=dt_timezone.utc)
        )  # Wed during DST, same time as self.reg_class1

        url = self.classes_url + '?name=Class 1&day=03WE&time=1800'
        resp = self.client.get(url)
        assert len(resp.context_data['events']) == 2
        assert[ev.id for ev in resp.context_data['events']] == [self.reg_class1.id, reg_class3.id]

    def test_outstanding_fees_shows_banner(self):
        baker.make_recipe("booking.booking", user=self.user, event=self.reg_class1, status="CANCELLED", cancellation_fee_incurred=True)
        resp = self.client.get(self.classes_url)
        assert "Your account is locked for booking due to outstanding fees" in resp.rendered_content

    def test_buttons_disabled_if_user_has_outstanding_fees(self):
        baker.make_recipe("booking.booking", user=self.user, event=self.events[0], status="CANCELLED", cancellation_fee_incurred=True)

        # full event - join waiting list will be disabled
        full_event = baker.make_recipe('booking.future_PC', max_participants=1)
        baker.make_recipe('booking.booking', event=full_event)

        resp = self.client.get(self.classes_url)
        assert 'id="book_button_disabled"' in resp.rendered_content  # for the cancelled booking
        assert 'id="join_waiting_list_button_disabled"' in resp.rendered_content

    def test_event_list_cleans_up_expired_bookings(self):
        """
        Test that all events are listed (workshops and other events)
        """
        cache.clear()
        now = timezone.now()
        # booked > 15 mins ago
        baker.make(
            "booking.booking", event=self.reg_class1, paid=False, 
            date_booked=now - timedelta(minutes=30)
        )
        # booked > 15 mins ago, rebooked < 15 mins ago
        rebooking = baker.make(
            "booking.booking", event=self.reg_class1, paid=False, 
            date_booked=now - timedelta(minutes=30),
            date_rebooked = now - timedelta(minutes=10)
        )
        # booked > 15 mins ago, but checkout_time < 5 mins ago
        checkedout_booking = baker.make(
            "booking.booking", event=self.reg_class2, paid=False, 
            date_booked=now - timedelta(minutes=30),
            checkout_time=now - timedelta(minutes=2)
        )
        self.client.get(self.workshops_url)
        # uses cache
        assert cache.get("expired_bookings_cleaned")
        self.reg_class1.refresh_from_db()
        self.reg_class2.refresh_from_db()
        
        assert self.reg_class1.bookings.count() == 1
        assert self.reg_class1.bookings.first().id == rebooking.id
        assert self.reg_class2.bookings.first().id == checkedout_booking.id
        
        # make another booking that's expired
        baker.make(
            "booking.booking", event=self.reg_class1, paid=False, date_booked=now - timedelta(minutes=30)
        )
        assert self.reg_class1.bookings.count() == 2
        # call events again; doesn't get cleaned up b/c cache hasn't expired yet
        self.client.get(self.workshops_url)
        self.reg_class1.refresh_from_db()
        assert self.reg_class1.bookings.count() == 2

        # delete cache item; now it gets cleaned up
        cache.delete("expired_bookings_cleaned")
        self.client.get(self.workshops_url)
        self.reg_class1.refresh_from_db()
        assert self.reg_class1.bookings.count() == 1


class EventDetailViewTests(TestSetupMixin, TestCase):

    @classmethod
    def setUpTestData(cls):
        super(EventDetailViewTests, cls).setUpTestData()
        make_online_disclaimer(user=cls.user)
        baker.make_recipe('booking.future_EV', _quantity=3)

    def setUp(self):
        self.event = baker.make_recipe('booking.future_EV')
        self.client.login(username=self.user.username, password='test')

    def url(self, event=None):
        event = event or self.event
        return reverse('booking:event_detail', args=[event.slug])

    def test_not_logged_in(self):
        """
        test that page loads if not logged in.
        No booking or waiting list buttons shown.
        """
        self.client.logout()
        resp = self.client.get(self.url())
        assert resp.status_code == 200
        assert resp.context_data['event_type'] == 'workshop'
        assert resp.context_data['booking_info_text'] == \
        f"Please <a href='/accounts/login?next=/booking/workshops/{self.event.slug}'>log in</a> to book."
        assert 'book_button' not in resp.rendered_content
        assert 'join_waiting_list_button' not in resp.rendered_content
        assert 'leave_waiting_list_button' not in resp.rendered_content

    def test_not_logged_in_full_event(self):
        """
        test that page loads if not logged in.
        No booking or waiting list buttons shown.
        """
        self.client.logout()
        self.event.max_participants = 3
        self.event.save()
        baker.make(Booking, event=self.event, _quantity=3)
        resp = self.client.get(self.url())

        assert resp.context_data['booking_info_text'] == (
            f"This workshop is now full.  Please <a href='/accounts/login?next=/booking/workshops/{self.event.slug}'>log in</a> "
            "to join the waiting list."
        )
        assert 'book_button' not in resp.rendered_content
        assert 'join_waiting_list_button' not in resp.rendered_content
        assert 'leave_waiting_list_button' not in resp.rendered_content

    def test_with_logged_in_user(self):
        """
        test that page loads if there user is available
        """
        resp = self.client.get(self.url())
        assert resp.status_code == 200
        assert resp.context_data['event_type'] == 'workshop'

    def test_user_on_waiting_list(self):
        resp = self.client.get(self.url())
        assert "waiting_list" not in resp.context_data
        
        baker.make(WaitingListUser, user=self.user, event=self.event)
        resp = self.client.get(self.url())
        assert "waiting_list" in resp.context_data

    def test_event_full(self):
        baker.make_recipe("booking.booking", event=self.event, _quantity=self.event.max_participants)
        resp = self.client.get(self.url())
        assert resp.context_data['booking_info_text'] == "This workshop is now full."

    def test_show_on_site(self):
        self.client.logout()
        # can get if show on site
        resp = self.client.get(self.url())
        assert resp.status_code == 200

        # can't get if not show on site
        self.event.show_on_site = False
        self.event.save()
        resp = self.client.get(self.url())
        assert resp.status_code == 404

        # still can't get if not show on site and logged in as normal user
        self.client.login(username=self.user.username, password='test')
        resp = self.client.get(self.url())
        assert resp.status_code == 404

        # can get if logged in as staff user
        self.user.is_staff = True
        self.user.save()
        resp = self.client.get(self.url())
        assert resp.status_code == 200
        assert 'PREVIEW ONLY: THIS PAGE IS NOT VISIBLE TO NON-STAFF USERS' in resp.rendered_content

    def test_with_booked_event(self):
        """
        Test that booked event is shown as booked
        """
        #create a booking for this event and user
        baker.make_recipe('booking.booking', user=self.user, event=self.event)
        resp = self.client.get(self.url())
        assert resp.context_data['booked']
        assert resp.context_data['booking_info_text'] == 'You have booked for this workshop.'

    def test_with_booked_event_for_different_user(self):
        """
        Test that the event is not shown as booked if the current user has
        not booked it
        """
        user1 = baker.make_recipe('booking.user')
        #create a booking for this event and a different user
        baker.make_recipe('booking.booking', user=user1, event=self.event)

        resp = self.client.get(self.url())
        assert 'booked' not in resp.context_data
        assert resp.context_data['booking_info_text'] == ''

    def test_cancellation_information_displayed_cancellation_period(self):
        """
        If booking cancellation allowed, show cancellation period if there
        is one
        If booking cancellation not allowed, show nonrefundable message
        """
        self.event.cost = 10
        self.event.save()

        assert self.event.allow_booking_cancellation
        assert self.event.cancellation_period == 24

        resp = self.client.get(self.url())

        # show cancellation period and due date text
        assert 'Cancellation is allowed up to 24 hours prior to the workshop' in format_content(resp.rendered_content)

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

        assert self.event.cancellation_period == 24

        resp = self.client.get(self.url())

        # don't show cancellation period and due date text
        assert 'Cancellation is allowed up to 12 hours prior to the workshop ' \
            not in format_content(resp.rendered_content)
        booking_info = "Bookings are final and non-refundable; if you cancel your " \
                        "booking you will not be eligible for any refund or credit."
        
        assert booking_info in format_content(resp.rendered_content)

    def test_past_event(self):
        past_event = baker.make_recipe('booking.past_event')
        resp = self.client.get(self.url(past_event))
        assert resp.context_data['past']
        assert 'book_button' not in resp.rendered_content
        assert 'join_waiting_list_button' not in resp.rendered_content
        assert 'leave_waiting_list_button' not in resp.rendered_content

    def test_cancelled_booking(self):
        # create a cancelled booking for this event and user
        baker.make_recipe(
            'booking.booking', user=self.user, event=self.event,
            status='CANCELLED'
        )
        resp = self.client.get(self.url())
        assert resp.context_data['cancelled']
        assert resp.context_data['booking_info_text'] == ''
        assert resp.context_data['booking_info_text_cancelled'] == \
        "You have previously booked for this workshop and your booking has been cancelled."

    def test_no_show_booking(self):
        """
        No show booking displays as cancelled to user
        """
        # create a no_show booking for this event and user
        baker.make_recipe(
            'booking.booking', user=self.user, event=self.event,
            status='OPEN', no_show=True
        )
        resp = self.client.get(self.url())
        assert resp.context_data['cancelled']
        assert resp.context_data['booking_info_text'] == ''
        assert resp.context_data['booking_info_text_cancelled'] == \
        "You have previously booked for this workshop and your booking has been cancelled."

    def test_outstanding_fees_shows_banner(self):
        baker.make_recipe("booking.booking", event__cancellation_fee=1.00, user=self.user, status="CANCELLED", cancellation_fee_incurred=True)
        resp = self.client.get(self.url())
        assert "Your account is locked for booking due to outstanding fees" in resp.rendered_content
