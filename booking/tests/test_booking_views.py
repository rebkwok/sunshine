# -*- coding: utf-8 -*-
from datetime import datetime
from unittest.mock import Mock, patch
from model_mommy import mommy

from django.conf import settings
from django.core import mail
from django.urls import reverse
from django.test import TestCase, RequestFactory
from django.contrib.messages.storage.fallback import FallbackStorage
from django.utils import timezone

from accounts.models import DataPrivacyPolicy

from activitylog.models import ActivityLog

from booking.models import Event, Booking, WaitingListUser
from booking.views import BookingListView, BookingHistoryListView, \
    BookingCreateView, BookingDeleteView, BookingUpdateView, \
    duplicate_booking, fully_booked, cancellation_period_past, \
    update_booking_cancelled
from booking.tests.helpers import _create_session, TestSetupMixin

from payments.models import create_paypal_transaction


class BookingListViewTests(TestSetupMixin, TestCase):

    @classmethod
    def setUpTestData(cls):
        super(BookingListViewTests, cls).setUpTestData()
        cls.regular_sessions = mommy.make_recipe('booking.future_PC', _quantity=3)
        cls.events = mommy.make_recipe('booking.future_EV', _quantity=2)
        [mommy.make_recipe(
            'booking.booking', user=cls.user,
            event=event) for event in cls.regular_sessions]
        [mommy.make_recipe(
            'booking.booking', user=cls.user,
            event=event) for event in cls.events]
        mommy.make_recipe('booking.past_booking', user=cls.user)
        cls.url = reverse('booking:bookings')
        cls.url_workshops = reverse('booking:bookings') + '?type=workshop'

    def setUp(self):
        super(BookingListViewTests, self).setUp()
        self.client.login(username=self.user.username, password='test')

    def test_login_required(self):
        """
        test that page redirects if there is no user logged in
        """
        self.client.logout()
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 302)

    def test_booking_list(self):
        """
        Test that only future bookings for relevant event type are listed)
        """
        resp = self.client.get(self.url)
        self.assertEquals(Booking.objects.all().count(), 6)
        self.assertEquals(resp.status_code, 200)
        self.assertEquals(resp.context_data['bookings'].count(), 3)
        for booking in resp.context_data['bookings']:
            self.assertEquals(booking.event.event_type, 'regular_session')

        resp = self.client.get(self.url_workshops)
        self.assertEquals(resp.context_data['bookings'].count(), 2)
        for booking in resp.context_data['bookings']:
            self.assertEquals(booking.event.event_type, 'workshop')

    def test_data_policy_agreement_required(self):
        mommy.make(DataPrivacyPolicy)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse('accounts:data_privacy_review') + '?next={}'.format(self.url))

    def test_booking_list_by_user(self):
        """
        Test that only bookings for this user are listed
        """
        another_user = mommy.make_recipe('booking.user')
        mommy.make_recipe(
            'booking.booking', user=another_user, event=self.regular_sessions[0]
        )
        # check there are now 7 bookings
        self.assertEquals(Booking.objects.all().count(), 7)
        resp = self.client.get(self.url)
        # event listing should still only show this user's future bookings
        self.assertEquals(resp.context_data['bookings'].count(), 3)

    def test_workshop_booking_list_by_user(self):
        """
        Test that only bookings for this user are listed
        """
        another_user = mommy.make_recipe('booking.user')
        mommy.make_recipe(
            'booking.booking', user=another_user, event=self.events[0]
        )
        # check there are now 7 bookings
        self.assertEquals(Booking.objects.all().count(), 7)
        resp = self.client.get(self.url_workshops)

        # event listing should still only show this user's future bookings
        self.assertEquals(resp.context_data['bookings'].count(), 2)

    def test_cancelled_booking_shown_in_booking_list(self):
        """
        Test that all future bookings for this user are listed
        """
        ev = mommy.make_recipe('booking.future_PC', name="future event")
        mommy.make_recipe(
            'booking.booking', user=self.user, event=ev,
            status='CANCELLED'
        )
        # check there are now 7 bookings (3 future, 1 past, 2 workshops,  1 cancelled)
        self.assertEquals(Booking.objects.all().count(), 7)
        resp = self.client.get(self.url)

        # booking listing should show this user's future bookings,
        # including the cancelled one
        self.assertEquals(resp.context_data['bookings'].count(), 4)

    def test_paid_status_display(self):
        Event.objects.all().delete()
        Booking.objects.all().delete()
        event_with_cost = mommy.make_recipe('booking.future_PC', cost=10)

        mommy.make_recipe(
            'booking.booking', user=self.user, event=event_with_cost,
            paid=True
        )
        resp = self.client.get(self.url)
        self.assertIn(
            '<span class="confirmed fas fa-check"></span>',
            resp.rendered_content
        )

    def test_paid_status_display_workshops(self):
        Event.objects.all().delete()
        Booking.objects.all().delete()
        event_with_cost = mommy.make_recipe('booking.future_EV', cost=10)

        mommy.make_recipe(
            'booking.booking', user=self.user, event=event_with_cost,
            paid=True
        )
        resp = self.client.get(self.url + '?type=workshop')
        self.assertIn(
            '<span class="confirmed fas fa-check"></span>',
            resp.rendered_content
        )

    def test_paypalforms_for_unpaid_workshops_only(self):
        Event.objects.all().delete()
        Booking.objects.all().delete()
        class_with_cost = mommy.make_recipe('booking.future_PC', cost=10)
        event_with_cost = mommy.make_recipe('booking.future_EV', cost=10)

        mommy.make_recipe(
            'booking.booking', user=self.user, event=class_with_cost,
            paid=False
        )
        mommy.make_recipe(
            'booking.booking', user=self.user, event=event_with_cost,
            paid=False
        )
        resp = self.client.get(self.url)
        self.assertEqual(len(resp.context_data['paypalforms']), 0)

        resp = self.client.get(self.url_workshops)
        self.assertEqual(len(resp.context_data['paypalforms']), 1)


class BookingHistoryListViewTests(TestSetupMixin, TestCase):

    @classmethod
    def setUpTestData(cls):
        super(BookingHistoryListViewTests, cls).setUpTestData()
        event = mommy.make_recipe('booking.future_PC')
        cls.booking = mommy.make_recipe(
            'booking.booking', user=cls.user, event=event
        )
        cls.past_booking = mommy.make_recipe(
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
        self.assertEqual(resp.status_code, 302)

    def test_booking_history_list(self):
        """
        Test that only past bookings are listed)
        """
        resp = self._get_response(self.user)

        self.assertEquals(Booking.objects.all().count(), 2)
        self.assertEquals(resp.status_code, 200)
        self.assertEquals(resp.context_data['bookings'].count(), 1)

    def test_booking_history_list_by_user(self):
        """
        Test that only past booking for this user are listed
        """
        another_user = mommy.make_recipe('booking.user')
        mommy.make_recipe(
            'booking.booking', user=another_user, event=self.past_booking.event
        )
        # check there are now 3 bookings
        self.assertEquals(Booking.objects.all().count(), 3)
        resp = self._get_response(self.user)

        #  listing should still only show this user's past bookings
        self.assertEquals(resp.context_data['bookings'].count(), 1)


class BookingCreateViewTests(TestSetupMixin, TestCase):

    def _post_response(self, user, event, form_data={}):
        url = reverse('booking:book_event', kwargs={'event_slug': event.slug})
        store = _create_session()
        form_data['event'] = event.id
        request = self.factory.post(url, form_data)
        request.session = store
        request.user = user
        messages = FallbackStorage(request)
        request._messages = messages
        view = BookingCreateView.as_view()
        return view(request, event_slug=event.slug)

    def _get_response(self, user, event):
        url = reverse('booking:book_event', kwargs={'event_slug': event.slug})
        store = _create_session()
        request = self.factory.get(url, {'event': event.id})
        request.session = store
        request.user = user
        messages = FallbackStorage(request)
        request._messages = messages
        view = BookingCreateView.as_view()
        return view(request, event_slug=event.slug)

    def test_get_create_booking_page(self):
        """
        Get the booking page with the event context
        """
        event = mommy.make_recipe('booking.future_EV', max_participants=3)
        resp = self._get_response(self.user, event)
        self.assertEqual(resp.context_data['event'], event)

    def test_create_booking(self):
        """
        Test creating a booking
        """
        event = mommy.make_recipe('booking.future_EV', max_participants=3)
        self.assertEqual(Booking.objects.all().count(), 0)
        self._post_response(self.user, event)
        self.assertEqual(Booking.objects.all().count(), 1)

    def test_create_booking_sends_email(self):
        """
        Test creating a booking sends email to user only if not on event
        """
        event = mommy.make_recipe(
            'booking.future_EV', max_participants=3,
            email_studio_when_booked=True
        )
        self.assertEqual(Booking.objects.all().count(), 0)
        self._post_response(self.user, event)
        self.assertEqual(Booking.objects.all().count(), 1)
        # email to student and studio
        self.assertEqual(len(mail.outbox), 2)

    def test_create_booking_sends_email_to_studio(self):
        """
        Test creating a booking send email to user and studio
        """
        event = mommy.make_recipe(
            'booking.future_EV', max_participants=3,
        )
        self.assertEqual(Booking.objects.all().count(), 0)
        self._post_response(self.user, event)
        self.assertEqual(Booking.objects.all().count(), 1)
        # email to student and studio
        self.assertEqual(len(mail.outbox), 2)

    @patch('booking.email_helpers.EmailMultiAlternatives.send')
    def test_create_booking_with_all_email_error(self, mock_send_emails):
        """
        Test if all emails fail when creating a booking
        """
        mock_send_emails.side_effect = Exception('Error sending mail')

        event = mommy.make_recipe(
            'booking.future_EV', max_participants=3,
            email_studio_when_booked=True
        )
        self.assertEqual(Booking.objects.all().count(), 0)
        self._post_response(self.user, event)
        self.assertEqual(Booking.objects.all().count(), 1)
        # no emails sent
        self.assertEqual(len(mail.outbox), 0)

        # exception is logged in activity log
        log = ActivityLog.objects.last()
        self.assertEqual(
            log.log,
            'Problem sending an email '
            '(booking.email_helpers.send_email: Error sending mail)'
        )

    def test_cannot_get_create_page_for_duplicate_booking(self):
        """
        Test trying to get the create page for existing redirects
        """
        event = mommy.make_recipe('booking.future_EV', max_participants=3)

        resp = self._post_response(self.user, event)
        booking = Booking.objects.latest('id')
        booking_url = reverse('booking:update_booking', args=[booking.id])
        self.assertEqual(resp.url, booking_url)

        resp1 = self._get_response(self.user, event)
        duplicate_url = reverse('booking:duplicate_booking',
                                kwargs={'event_slug': event.slug}
                                )
        # test redirect to duplicate booking url
        self.assertEqual(resp1.url, duplicate_url)

    def test_cannot_create_duplicate_booking(self):
        """
        Test trying to create a duplicate booking redirects
        """
        event = mommy.make_recipe('booking.future_EV', max_participants=3)

        resp = self._post_response(self.user, event)
        booking = Booking.objects.latest('id')
        booking_url = reverse('booking:update_booking', args=[booking.id])
        self.assertEqual(resp.url, booking_url)

        resp1 = self._post_response(self.user, event)
        duplicate_url = reverse('booking:duplicate_booking',
                                kwargs={'event_slug': event.slug}
                                )
        # test redirect to duplicate booking url
        self.assertEqual(resp1.url, duplicate_url)

    def test_cannot_get_create_booking_page_for_full_event(self):
        """
        Test trying to get create booking page for a full event redirects
        """
        event = mommy.make_recipe('booking.future_EV', max_participants=3)
        users = mommy.make_recipe('booking.user', _quantity=3)
        for user in users:
            mommy.make_recipe('booking.booking', event=event, user=user)
        # check event is full; we need to get the event again as spaces_left is
        # cached property
        event = Event.objects.get(id=event.id)
        self.assertEqual(event.spaces_left, 0)

        # try to book for event
        resp = self._get_response(self.user, event)
        # test redirect to duplicate booking url
        self.assertEqual(
            resp.url,
            reverse(
                'booking:fully_booked',
                kwargs={'event_slug': event.slug}
            )
        )

    def test_cannot_book_for_full_event(self):
        """cannot create booking for a full event
        """
        event = mommy.make_recipe('booking.future_EV', max_participants=3)
        users = mommy.make_recipe('booking.user', _quantity=3)
        for user in users:
            mommy.make_recipe('booking.booking', event=event, user=user)

        # check event is full; we need to get the event again as spaces_left is
        # cached property
        event = Event.objects.get(id=event.id)
        self.assertEqual(event.spaces_left, 0)

        # try to book for event
        resp = self._post_response(self.user, event)

        # test redirect to duplicate booking url
        self.assertEqual(
            resp.url,
            reverse(
                'booking:fully_booked',
                kwargs={'event_slug': event.slug}
            )
        )

    def test_cancelled_booking_can_be_rebooked(self):
        """
        Test can load create booking page with a cancelled booking
        """

        event = mommy.make_recipe('booking.future_EV')
        # book for event
        self._post_response(self.user, event)

        booking = Booking.objects.get(user=self.user, event=event)
        # cancel booking
        booking.status = 'CANCELLED'
        booking.save()

        # try to book again
        resp = self._get_response(self.user, event)
        self.assertEqual(resp.status_code, 200)

    def test_no_show_booking_can_be_rebooked(self):
        """
        Test can load create booking page with a no_show open booking
        """
        event = mommy.make_recipe(
            'booking.future_EV', allow_booking_cancellation=False, cost=10
        )

        # book for non-refundable event and mark as no_show
        booking = mommy.make_recipe(
            'booking.booking', user=self.user, event=event, paid=True,
            no_show=True, status='OPEN'
        )

        # try to get booking page again
        self.client.login(username=self.user.username, password='test')
        resp = self.client.get(
            reverse('booking:book_event', kwargs={'event_slug': event.slug}),
        )
        self.assertEqual(resp.status_code, 200)

    def test_rebook_cancelled_booking(self):
        """
        Test can rebook a cancelled booking
        """

        event = mommy.make_recipe('booking.future_EV')
        # book for event
        self._post_response(self.user, event)

        booking = Booking.objects.get(user=self.user, event=event)
        # cancel booking
        booking.status = 'CANCELLED'
        booking.save()
        self.assertIsNone(booking.date_rebooked)

        # try to book again
        self._post_response(self.user, event)
        booking.refresh_from_db()
        self.assertEqual('OPEN', booking.status)
        self.assertIsNotNone(booking.date_rebooked)

    def test_rebook_no_show_booking(self):
        """
        Test can rebook a booking marked as no_show
        """

        event = mommy.make_recipe(
            'booking.future_EV', allow_booking_cancellation=False, cost=10
        )
        # book for non-refundable event and mark as no_show
        booking = mommy.make_recipe(
            'booking.booking', user=self.user, event=event, paid=True,
            no_show=True
        )
        self.assertIsNone(booking.date_rebooked)

        # try to book again
        self.client.login(username=self.user.username, password='test')
        resp = self.client.post(
            reverse('booking:book_event', kwargs={'event_slug': event.slug}),
            {'event': event.id},
            follow=True
        )
        booking.refresh_from_db()
        self.assertEqual('OPEN', booking.status)
        self.assertFalse(booking.no_show)
        self.assertIsNotNone(booking.date_rebooked)
        self.assertIn(
            "You previously paid for this booking and your "
            "booking has been reopened.",
            resp.rendered_content
        )

        # emails sent to student and studio by default
        self.assertEqual(len(mail.outbox), 2)
        email = mail.outbox[0]
        self.assertEqual(email.to, ['test@test.com'])
        studio_email = mail.outbox[1]
        self.assertEqual(studio_email.to, [settings.DEFAULT_STUDIO_EMAIL])

    def test_rebook_cancelled_paid_booking(self):

        """
        Test rebooking a cancelled booking still marked as paid reopend booking
        and emails studi
        """
        event = mommy.make_recipe('booking.future_EV')
        mommy.make_recipe(
            'booking.booking', event=event, user=self.user, paid=True,
            status='CANCELLED'
        )

        # try to book again
        self._post_response(self.user, event)
        booking = Booking.objects.get(user=self.user, event=event)
        self.assertEqual('OPEN', booking.status)
        self.assertTrue(booking.paid)

        # email to user and to studio
        self.assertEqual(len(mail.outbox), 2)
        mail_to_user = mail.outbox[0]
        mail_to_studio = mail.outbox[1]

        self.assertEqual(mail_to_user.to, [self.user.email])
        self.assertEqual(mail_to_studio.to, [settings.DEFAULT_STUDIO_EMAIL])

    def test_rebook_cancelled_paypal_paid_booking(self):

        """
        Test rebooking a cancelled booking still marked as paid by paypal makes
        booking status open but does not confirm space, fetches the paypal
        transaction id
        """
        event = mommy.make_recipe('booking.future_EV')
        booking = mommy.make_recipe(
            'booking.booking', event=event, user=self.user, paid=True,
            status='CANCELLED'
        )
        pptrans = create_paypal_transaction(booking=booking, user=self.user)
        pptrans.transaction_id = "txn"
        pptrans.save()

        # try to book again
        self._post_response(self.user, event)
        booking = Booking.objects.get(user=self.user, event=event)
        self.assertEqual('OPEN', booking.status)
        self.assertTrue(booking.paid)

        # email to user and to studio
        self.assertEqual(len(mail.outbox), 2)
        mail_to_user = mail.outbox[0]
        mail_to_studio = mail.outbox[1]

        self.assertEqual(mail_to_user.to, [self.user.email])
        self.assertEqual(mail_to_studio.to, [settings.DEFAULT_STUDIO_EMAIL])
        self.assertIn(pptrans.transaction_id, mail_to_studio.body)
        self.assertIn(pptrans.invoice_id, mail_to_studio.body)

    def test_create_booking_sets_flag_on_session(self):
        self.client.login(username=self.user.username, password='test')
        event = mommy.make_recipe('booking.future_EV')
        self.client.post(
            reverse('booking:book_event', kwargs={'event_slug': event.slug}),
            {'event': event.id}
        )
        booking = Booking.objects.latest('id')
        self.assertIn(
            'booking_created_{}'.format(booking.id), self.client.session.keys()
        )

    def test_create_booking_redirects_to_events_if_flag_on_session(self):
        """
        When a booking is created, "booking_created" flag is set on the
        session so that if the user clicks the back button they get returned
        to the events list page instead of the create booking page again
        """
        event = mommy.make_recipe('booking.future_EV')
        url = reverse('booking:book_event', kwargs={'event_slug': event.slug})
        self.client.login(username=self.user.username, password='test')
        booking = mommy.make_recipe(
            'booking.booking', event=event, user=self.user
        )

        # with no flag, redirects to duplicate booking page
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 302)
        self.assertIn(
            resp.url,
            reverse(
                'booking:duplicate_booking', kwargs={'event_slug': event.slug}
            )
        )

        # with flag, redirects to events page
        booking.delete()
        self.client.post(
            reverse('booking:book_event', kwargs={'event_slug': event.slug}),
            {'event': event.id}
        )
        booking = Booking.objects.latest('id')
        self.assertIn(
            'booking_created_{}'.format(booking.id), self.client.session.keys()
        )

        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 302)
        self.assertIn(resp.url, reverse('booking:events'))
        # flag has been removed
        self.assertNotIn(
            'booking_created_{}'.format(booking.id), self.client.session.keys()
        )

    def test_reopen_booking_does_not_redirect_if_flag_on_session(self):
        """
        A user might create a booking, cancel it, and immediately try to
        rebook while the booking_created flag is still on the session.  In this
        case, allow the booking page to be retrieved
        """
        event = mommy.make_recipe('booking.future_EV')
        url = reverse('booking:book_event', kwargs={'event_slug': event.slug})
        self.client.login(username=self.user.username, password='test')

        self.client.post(url, {'event': event.id})
        booking = Booking.objects.latest('id')
        self.assertIn(
            'booking_created_{}'.format(booking.id), self.client.session.keys()
        )

        booking.status = 'CANCELLED'
        booking.save()
        # with flag, still gets the create booking page
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)


class BookingErrorRedirectPagesTests(TestSetupMixin, TestCase):

    def _get_duplicate_booking(self, user, event):
        url = reverse(
            'booking:duplicate_booking', kwargs={'event_slug': event.slug}
        )
        session = _create_session()
        request = self.factory.get(url)
        request.session = session
        request.user = user
        messages = FallbackStorage(request)
        request._messages = messages
        return duplicate_booking(request, event.slug)

    def _get_fully_booked(self, user, event):
        url = reverse(
            'booking:fully_booked', kwargs={'event_slug': event.slug}
        )
        session = _create_session()
        request = self.factory.get(url)
        request.session = session
        request.user = user
        messages = FallbackStorage(request)
        request._messages = messages
        return fully_booked(request, event.slug)

    def _get_update_booking_cancelled(self, user, booking):
        url = reverse(
            'booking:update_booking_cancelled', kwargs={'pk': booking.pk}
        )
        session = _create_session()
        request = self.factory.get(url)
        request.session = session
        request.user = user
        messages = FallbackStorage(request)
        request._messages = messages
        return update_booking_cancelled(request, booking.pk)

    def test_duplicate_event_booking(self):
        """
        Get the duplicate booking page with the event context
        """
        event = mommy.make_recipe('booking.future_EV')
        resp = self._get_duplicate_booking(self.user, event)
        self.assertIn(event.name, str(resp.content))

    def test_fully_booked(self):
        """
        Get the fully booked page with the event context
        """
        event = mommy.make_recipe('booking.future_EV')
        resp = self._get_fully_booked(self.user, event)
        self.assertIn(event.name, str(resp.content))

    def test_update_booking_cancelled(self):
        """
        Get the redirected page when trying to update a cancelled booking
        with the event context
        """
        event = mommy.make_recipe('booking.future_EV')
        booking = mommy.make_recipe(
            'booking.booking', status='CANCELLED', event=event
        )
        resp = self._get_update_booking_cancelled(self.user, booking)
        self.assertIn(event.name, str(resp.content))


    def test_update_booking_cancelled_for_full_event(self):
        """
        Get the redirected page when trying to update a cancelled booking
        for an event that's now full
        """
        event = mommy.make_recipe('booking.future_EV', max_participants=3)
        booking = mommy.make_recipe(
            'booking.booking', status='CANCELLED', event=event
        )
        mommy.make_recipe(
            'booking.booking', status='OPEN', event=event, _quantity=3
        )
        # check event is full; we need to get the event again as spaces_left is
        # cached property
        event = Event.objects.get(id=event.id)
        self.assertEqual(event.spaces_left, 0)
        resp = self._get_update_booking_cancelled(self.user, booking)
        self.assertIn(event.name, str(resp.content))
        self.assertIn("This workshop is now full", str(resp.content))

    def test_already_cancelled(self):
        """
        Get the redirected page when trying to cancel a cancelled booking
        for an event that's now full
        """
        booking = mommy.make_recipe('booking.booking', status='CANCELLED')
        resp = self.client.get(
            reverse('booking:already_cancelled', args=[booking.id])
        )
        self.assertIn(booking.event.name, str(resp.content))

    def test_cannot_cancel_after_cancellation_period(self):
        """
        Get the cannot cancel page with the event context
        """
        event = mommy.make_recipe('booking.future_EV')
        url = reverse(
            'booking:cancellation_period_past',
            kwargs={'event_slug': event.slug}
        )
        session = _create_session()
        request = self.factory.get(url)
        request.session = session
        request.user = self.user
        messages = FallbackStorage(request)
        request._messages = messages
        resp = cancellation_period_past(request, event.slug)
        self.assertIn(event.name, str(resp.content))

    def test_already_paid(self):
        booking = mommy.make_recipe('booking.booking', paid=True)
        resp = self.client.get(
            reverse('booking:already_paid', args=[booking.id])
        )
        self.assertIn(booking.event.name, str(resp.content))


class BookingDeleteViewTests(TestSetupMixin, TestCase):

    def _delete_response(self, user, booking):
        url = reverse('booking:delete_booking', args=[booking.id])
        session = _create_session()
        request = self.factory.delete(url)
        request.session = session
        request.user = user
        messages = FallbackStorage(request)
        request._messages = messages
        view = BookingDeleteView.as_view()
        return view(request, pk=booking.id)

    def test_get_delete_booking_page(self):
        """
        Get the delete booking page with the event context
        """
        event = mommy.make_recipe('booking.future_EV')
        booking = mommy.make_recipe('booking.booking', event=event, user=self.user)
        url = reverse(
            'booking:delete_booking', args=[booking.id]
        )
        session = _create_session()
        request = self.factory.get(url)
        request.session = session
        request.user = self.user
        messages = FallbackStorage(request)
        request._messages = messages
        view = BookingDeleteView.as_view()
        resp = view(request, pk=booking.id)
        self.assertEqual(resp.context_data['event'], event)

    def test_cancel_booking(self):
        """
        Test deleting a booking
        """
        event = mommy.make_recipe('booking.future_EV')
        booking = mommy.make_recipe('booking.booking', event=event,
                                    user=self.user)
        self.assertEqual(Booking.objects.all().count(), 1)
        self._delete_response(self.user, booking)
        # after cancelling, the booking is still there, but status has changed
        self.assertEqual(Booking.objects.all().count(), 1)
        booking = Booking.objects.get(id=booking.id)
        self.assertEqual('CANCELLED', booking.status)

    def test_cancelling_only_this_booking(self):
        """
        Test cancelling a booking when user has more than one
        """
        events = mommy.make_recipe('booking.future_EV', _quantity=3)

        for event in events:
            mommy.make_recipe('booking.booking', user=self.user, event=event)

        self.assertEqual(Booking.objects.all().count(), 3)
        booking = Booking.objects.all()[0]
        self._delete_response(self.user, booking)
        self.assertEqual(Booking.objects.all().count(), 3)
        cancelled_bookings = Booking.objects.filter(status='CANCELLED')
        self.assertEqual([cancelled.id for cancelled in cancelled_bookings],
                         [booking.id])

    @patch("booking.views.booking_views.timezone")
    def test_can_cancel_after_cancellation_period(self, mock_tz):
        """
        Test trying to cancel after cancellation period
        Cancellation is allowed but shows warning message
        """
        mock_tz.now.return_value = datetime(2015, 2, 1, tzinfo=timezone.utc)
        event = mommy.make_recipe(
            'booking.future_EV',
            date=datetime(2015, 2, 2, tzinfo=timezone.utc),
            cancellation_period=48
        )
        booking = mommy.make_recipe(
            'booking.booking', event=event, user=self.user
        )

        url = reverse('booking:delete_booking', args=[booking.id])
        self.client.login(username=self.user.username, password='test')
        resp = self.client.get(url)

        self.assertEqual(200, resp.status_code)
        self.assertIn(
            'If you continue, you will not be eligible for any refunds.',
            resp.rendered_content
        )

    @patch("booking.views.booking_views.timezone")
    def test_cancelling_after_cancellation_period(self, mock_tz):
        """
        Test cancellation after cancellation period sets no_show to True
        """
        mock_tz.now.return_value = datetime(2015, 2, 1, tzinfo=timezone.utc)
        event = mommy.make_recipe(
            'booking.future_EV',
            date=datetime(2015, 2, 2, tzinfo=timezone.utc),
            cancellation_period=48
        )
        booking = mommy.make_recipe(
            'booking.booking', event=event, user=self.user, paid=True
        )

        url = reverse('booking:delete_booking', args=[booking.id])
        self.client.login(username=self.user.username, password='test')
        resp = self.client.delete(url, follow=True)
        self.assertIn(
            'Please note that this booking is not eligible for refunds '
            'as the allowed cancellation period has passed.',
            resp.rendered_content
        )
        booking.refresh_from_db()
        self.assertTrue(booking.no_show)
        self.assertEqual(booking.status, 'OPEN')
        self.assertTrue(booking.paid)

    def test_cannot_cancel_twice(self):
        event = mommy.make_recipe('booking.future_EV')
        booking = mommy.make_recipe('booking.booking', event=event,
                                    user=self.user)
        self.assertEqual(Booking.objects.all().count(), 1)
        self._delete_response(self.user, booking)
        booking.refresh_from_db()
        self.assertEqual('CANCELLED', booking.status)

        # try deleting again, should redirect
        resp = self._delete_response(self.user, booking)
        self.assertEqual(resp.status_code, 302)
        self.assertIn(
            resp.url, reverse('booking:already_cancelled', args=[booking.id])
        )

    def test_event_with_cancellation_not_allowed(self):
        """
        Can still be cancelled but not refundable
        Paid booking stays OPEN but is set to no_show
        Unpaid booking is just cancelled
        """
        event = mommy.make_recipe(
            'booking.future_EV', allow_booking_cancellation=False
        )
        paid_booking = mommy.make_recipe('booking.booking', event=event,
                                    user=self.user, paid=True)
        resp = self._delete_response(self.user, paid_booking)
        paid_booking.refresh_from_db()
        # still open, but no_show
        self.assertEqual('OPEN', paid_booking.status)
        self.assertTrue(paid_booking.no_show)

        event1 = mommy.make_recipe(
            'booking.future_EV', allow_booking_cancellation=False
        )
        unpaid_booking = mommy.make_recipe(
            'booking.booking', event=event1, user=self.user
        )
        resp = self._delete_response(self.user, unpaid_booking)
        unpaid_booking.refresh_from_db()
        # cancelled
        self.assertEqual('CANCELLED', unpaid_booking.status)
        self.assertFalse(unpaid_booking.no_show)

    def test_cancelling_sends_email_to_user_and_studio_if_applicable(self):
        """ emails are always sent to user; only sent to studio if previously
        direct paid
        """
        event_with_cost = mommy.make_recipe('booking.future_EV', cost=10)
        booking = mommy.make_recipe(
            'booking.booking', user=self.user, event=event_with_cost,
        )
        self._delete_response(self.user, booking)
        # only 1 email sent for cancelled unpaid booking
        self.assertEqual(len(mail.outbox), 1)
        user_mail = mail.outbox[0]
        self.assertEqual(user_mail.to, [self.user.email])

        booking.refresh_from_db()
        booking.status = 'OPEN'
        booking.paid = True
        booking.save()
        self._delete_response(self.user, booking)
        # 2 emails sent this time for direct paid booking
        self.assertEqual(len(mail.outbox), 3)
        user_mail = mail.outbox[1]
        studio_mail = mail.outbox[2]
        self.assertEqual(user_mail.to, [self.user.email])
        self.assertEqual(studio_mail.to, [settings.DEFAULT_STUDIO_EMAIL])

    def test_cancelling_full_event_sends_waiting_list_emails(self):
        event = mommy.make_recipe(
            'booking.future_EV', cost=10, max_participants=3
        )
        booking = mommy.make_recipe(
            'booking.booking', user=self.user, event=event,
        )
        mommy.make_recipe('booking.booking', event=event, _quantity=2)
        wluser = mommy.make(
            WaitingListUser, event=event, user__email='wl@test.com'
        )

        self._delete_response(self.user, booking)
        self.assertEqual(len(mail.outbox), 2)
        user_mail = mail.outbox[0]
        waiting_list_mail = mail.outbox[1]
        self.assertEqual(user_mail.to, [self.user.email])
        self.assertEqual(waiting_list_mail.bcc, [wluser.user.email])

    @patch('booking.email_helpers.EmailMultiAlternatives.send')
    def test_errors_sending_waiting_list_emails(
            self, mock_send_wl_emails):
        mock_send_wl_emails.side_effect = Exception('Error sending mail')
        event = mommy.make_recipe(
            'booking.future_EV', cost=10, max_participants=3
        )
        booking = mommy.make_recipe(
            'booking.booking', user=self.user, event=event,
        )
        mommy.make_recipe('booking.booking', event=event, _quantity=2)
        mommy.make(
            WaitingListUser, event=event, user__email='wl@test.com'
        )

        self._delete_response(self.user, booking)

        self.assertEqual(len(mail.outbox), 0)
        log = ActivityLog.objects.latest('id')
        self.assertEqual(
            log.log,
            'Problem sending an email (booking.email_helpers.'
            'send_waiting_list_email: Error sending mail)'
        )

        booking.refresh_from_db()
        self.assertEqual(booking.status, 'CANCELLED')


class BookingUpdateViewTests(TestSetupMixin, TestCase):

    def _get_response(self, user, booking):
        url = reverse('booking:update_booking', args=[booking.id])
        session = _create_session()
        request = self.factory.get(url)
        request.session = session
        request.user = user
        messages = FallbackStorage(request)
        request._messages = messages

        view = BookingUpdateView.as_view()
        return view(request, pk=booking.id)

    def _post_response(self, user, booking, form_data):
        url = reverse('booking:update_booking', args=[booking.id])
        session = _create_session()
        request = self.factory.post(url, form_data)
        request.session = session
        request.user = user
        messages = FallbackStorage(request)
        request._messages = messages

        view = BookingUpdateView.as_view()
        return view(request, pk=booking.id)

    def test_can_get_page_for_open_booking(self):
        event = mommy.make_recipe('booking.future_EV', cost=10)
        booking = mommy.make_recipe(
            'booking.booking',
            user=self.user, event=event, paid=False
        )
        resp = self._get_response(self.user, booking)
        self.assertEqual(resp.status_code, 200)

    def test_cannot_get_page_for_paid_booking(self):
        event = mommy.make_recipe('booking.future_EV', cost=10)
        booking = mommy.make_recipe(
            'booking.booking',
            user=self.user, event=event, paid=True
        )
        resp = self._get_response(self.user, booking)
        self.assertEqual(resp.status_code, 302)
        self.assertIn(
            resp.url, reverse('booking:already_paid', args=[booking.pk])
        )
