# -*- coding: utf-8 -*-
import pytz
from datetime import date, datetime, timedelta
from unittest.mock import patch
from model_bakery import baker

from django.contrib.auth.models import User
from django.core import mail
from django.urls import reverse
from django.utils import timezone
from django.test import RequestFactory, TestCase

from booking.models import Event, WaitingListUser
from studioadmin.views.register import process_event_booking_updates
from studioadmin.forms import AddRegisterBookingForm
from .helpers import format_content, TestPermissionMixin


class EventRegisterListViewTests(TestPermissionMixin, TestCase):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.url = reverse('studioadmin:regular_session_register_list')
        cls.workshop_url = reverse('studioadmin:workshop_register_list')

    def setUp(self):
        super().setUp()
        self.client.login(username=self.staff_user.username, password="test")

    def test_cannot_access_if_not_logged_in(self):
        """
        test that the page redirects if user is not logged in
        """
        self.client.logout()
        resp = self.client.get(self.url)
        redirected_url = reverse('admin:login') + "?next={}".format(self.url)
        self.assertEqual(resp.status_code, 302)
        self.assertIn(redirected_url, resp.url)

    def test_can_access_as_staff_user(self):
        """
        test that the page can be accessed by a staff user
        """
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)

    def test_classes_context(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context_data['event_type'], 'regular_session')
        self.assertEqual(
            resp.context_data['regular_session_registers_menu_class'], 'active'
            )
        self.assertIn("Classes", resp.rendered_content)

    def test_workshop_context(self):
        resp = self.client.get(self.workshop_url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context_data['event_type'], 'workshop')
        self.assertEqual(
            resp.context_data['workshop_registers_menu_class'], 'active'
        )
        self.assertIn("Workshops", resp.rendered_content)

    def test_event_register_list_shows_future_events_only(self):
        baker.make_recipe('booking.future_PC', _quantity=4)
        baker.make_recipe('booking.past_class', _quantity=4)
        resp = self.client.get(self.url)
        self.assertEqual(len(resp.context_data['events']), 4)

    def test_event_register_list_shows_todays_events(self):
        baker.make_recipe('booking.future_PC', _quantity=4)
        baker.make_recipe('booking.past_class', _quantity=4)
        baker.make_recipe('booking.past_class', date=timezone.now().replace(hour=0, minute=1))
        resp = self.client.get(self.url)
        self.assertEqual(len(resp.context_data['events']), 5)

    def test_event_register_list_shows_event_in_next_week_by_default(self):
        baker.make_recipe('booking.future_PC', date=timezone.now() + timedelta(6), _quantity=4)
        baker.make_recipe('booking.future_PC', date=timezone.now() + timedelta(8))
        resp = self.client.get(self.url)
        self.assertEqual(len(resp.context_data['events']), 4)
        resp = self.client.get(self.url + "?show_all=true")
        self.assertEqual(len(resp.context_data['events']), 5)

    def test_event_register_list_shows_correct_booking_count(self):
        event = baker.make_recipe('booking.future_PC')
        baker.make_recipe('booking.booking', event=event, _quantity=2)
        baker.make_recipe('booking.booking', event=event, status='CANCELLED')
        baker.make_recipe('booking.booking', event=event, no_show=True)
        resp = self.client.get(self.url)
        self.assertIn(
            '{} {} 2'.format(
                event.date.astimezone(
                    pytz.timezone('Europe/London')
                ).strftime('%a %d %b, %H:%M'), event.name
            ),
            format_content(resp.rendered_content)
        )

    @patch("studioadmin.views.register.timezone")
    def test_register_shows_event_dates_in_local_time(self, mock_tz):
        mock_tz.now.return_value = datetime(2020, 7, 28, 18, 0, tzinfo=timezone.utc)
        # event during BST
        event = baker.make_recipe('booking.future_PC', date=datetime(2020, 8, 1, 18, 0, tzinfo=timezone.utc))
        resp = self.client.get(self.url)
        self.assertIn("Sat 01 Aug, 19:00", resp.rendered_content)


class RegisterViewTests(TestPermissionMixin, TestCase):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.pc = baker.make_recipe('booking.future_PC', max_participants=3)
        cls.pc_no_max = baker.make_recipe('booking.future_PC')
        cls.ev = baker.make_recipe('booking.future_EV', max_participants=3)
        cls.pc_url = reverse('studioadmin:event_register', args=(cls.pc.slug,))
        cls.pc_no_max_url = reverse('studioadmin:event_register', args=(cls.pc_no_max.slug,))
        cls.ev_url = reverse('studioadmin:event_register', args=(cls.ev.slug,))

    def setUp(self):
        super().setUp()
        self.client.login(username=self.staff_user.username, password='test')

    def test_login_required(self):
        self.client.logout()
        resp = self.client.get(self.pc_url)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse('account_login') + "?next={}".format(self.pc_url))

    def test_staff_or_instructor_required(self):
        self.client.logout()
        self.client.login(username=self.user.username, password='test')
        resp = self.client.get(self.pc_url)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse('admin:login') + "?next={}".format(self.pc_url))

        self.client.login(username=self.staff_user.username, password='test')
        resp = self.client.get(self.pc_url)
        self.assertEqual(resp.status_code, 200)

    def test_menu_selection(self):
        resp = self.client.get(self.pc_url)
        self.assertEqual(resp.context_data['regular_session_registers_menu_class'], 'active')

        resp = self.client.get(self.ev_url)
        self.assertEqual(resp.context_data['workshop_registers_menu_class'], 'active')

    def test_register_no_bookings(self):
        resp = self.client.get(self.pc_url)
        self.assertEqual(resp.context_data['event'], self.pc)
        self.assertFalse(resp.context_data['bookings'].exists())
        self.assertTrue(resp.context_data['can_add_more'])

    def test_register_shows_event_bookings(self):
        bookings = baker.make_recipe('booking.booking', status='OPEN', event=self.pc, _quantity=2)
        baker.make_recipe('booking.booking', status='OPEN', event=self.ev, _quantity=3)
        resp = self.client.get(self.pc_url)
        self.assertEqual(
            sorted([booking.id for booking in resp.context_data['bookings']]),
            sorted([booking.id for booking in bookings]))

    def test_cancelled_bookings_not_shown(self):
        bookings = baker.make_recipe('booking.booking', status='OPEN', event=self.pc, _quantity=2)
        baker.make_recipe('booking.booking', status='CANCELLED', event=self.pc, _quantity=2)
        resp = self.client.get(self.pc_url)
        self.assertEqual(
            sorted([booking.id for booking in resp.context_data['bookings']]),
            sorted([booking.id for booking in bookings]))

    def test_no_show_bookings_shown(self):
        bookings = baker.make_recipe('booking.booking', status='OPEN', event=self.pc, _quantity=2)
        no_show_bookings = baker.make_recipe('booking.booking', status='OPEN', no_show=True, event=self.pc, _quantity=1)
        resp = self.client.get(self.pc_url)
        self.assertEqual(
            sorted([booking.id for booking in resp.context_data['bookings']]),
            sorted([booking.id for booking in bookings + no_show_bookings]))

    def test_full_event_shows_no_new_booking_button(self):
        baker.make_recipe('booking.booking', status='OPEN', event=self.pc, _quantity=2)
        resp = self.client.get(self.pc_url)
        self.assertTrue(resp.context_data['can_add_more'])

        baker.make_recipe('booking.booking', status='OPEN', event=self.pc)
        resp = self.client.get(self.pc_url)
        self.assertFalse(resp.context_data['can_add_more'])

    def test_status_choices(self):
        open_bookings = baker.make_recipe('booking.booking', status='OPEN', event=self.pc, _quantity=2)
        cancelled_bookings = baker.make_recipe('booking.booking', status='CANCELLED', event=self.pc, _quantity=2)

        resp = self.client.get(self.pc_url + '?status_choice=CANCELLED')
        self.assertEqual(
            sorted([booking.id for booking in resp.context_data['bookings']]),
            sorted([booking.id for booking in cancelled_bookings])
        )

        resp = self.client.get(self.pc_url + '?status_choice=OPEN')
        self.assertEqual(
            sorted([booking.id for booking in resp.context_data['bookings']]),
            sorted([booking.id for booking in open_bookings])
        )

        resp = self.client.get(self.pc_url + '?status_choice=ALL')
        self.assertEqual(
            sorted([booking.id for booking in resp.context_data['bookings']]),
            sorted([booking.id for booking in open_bookings + cancelled_bookings])
        )


class RegisterAjaxAddBookingViewsTests(TestPermissionMixin, TestCase):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.pc = baker.make_recipe('booking.future_PC', max_participants=3)
        cls.ev = baker.make_recipe('booking.future_EV', max_participants=3)
        cls.pc_url = reverse('studioadmin:bookingregisteradd', args=(cls.pc.id,))
        cls.ev_url = reverse('studioadmin:bookingregisteradd', args=(cls.ev.id,))

    def setUp(self):
        super().setUp()
        self.client.login(username=self.staff_user.username, password='test')

    def test_add_booking_user_permissions(self):
        self.client.logout()
        resp = self.client.get(self.pc_url)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse('account_login') + "?next={}".format(self.pc_url))

        self.client.login(username=self.user.username, password='test')
        resp = self.client.get(self.pc_url)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse('admin:login') + "?next={}".format(self.pc_url))

        self.client.login(username=self.staff_user.username, password='test')
        resp = self.client.get(self.pc_url)
        self.assertEqual(resp.status_code, 200)

    def test_add_booking(self):
        self.assertFalse(self.pc.bookings.exists())
        self.client.post(self.pc_url, {'user': self.user.id})
        booking = self.pc.bookings.first()
        self.assertEqual(booking.user.id, self.user.id)
        self.assertEqual(booking.status, 'OPEN')
        self.assertFalse(booking.no_show)
        self.assertFalse(booking.paid)

    def test_reopen_cancelled_booking(self):
        booking = baker.make_recipe('booking.booking', user=self.user, event=self.pc, status='CANCELLED')
        self.assertEqual(self.pc.bookings.count(), 1)

        self.client.post(self.pc_url, {'user': booking.user.id})
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'OPEN')
        self.assertFalse(booking.no_show)

    def test_reopen_no_show_booking(self):
        booking = baker.make_recipe('booking.booking', user=self.user, event=self.pc, status='OPEN', no_show=True)
        self.assertEqual(self.pc.bookings.count(), 1)

        self.client.post(self.pc_url, {'user': booking.user.id})
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'OPEN')
        self.assertFalse(booking.no_show)

    def test_user_choices(self):
        user = baker.make_recipe('booking.user')
        user1 = baker.make_recipe('booking.user')
        user2 = baker.make_recipe('booking.user')
        # open booking
        baker.make_recipe('booking.booking', user=self.user, event=self.pc, status='OPEN')
        # no_show_booking
        baker.make_recipe('booking.booking', user=user, event=self.pc, status='OPEN', no_show=True)
        # cancelled_booking
        baker.make_recipe('booking.booking', user=user1, event=self.pc, status='CANCELLED')

        # form shows users with cancelled, no-show or no bookings
        form = AddRegisterBookingForm(event=self.pc)
        self.assertEqual(
            sorted([choice[0] for choice in form.fields['user'].choices]),
            sorted([user.id for user in User.objects.exclude(id=self.user.id)])
        )

    @patch('studioadmin.views.register.messages.info')
    def test_already_open_booking(self, mock_messages):
        # The user choices in the form exclude users with open bookings already, but we could post a form with an open
        # booking if the booking was made in another session and the add booking forw was still open

        # get the user form
        form = AddRegisterBookingForm({'user': self.user.id}, event=self.pc)
        self.assertTrue(form.is_valid())

        # make booking for this user
        baker.make_recipe('booking.booking', user=self.user, event=self.pc, status='OPEN')

        # try to process the form
        request = self.factory.get(self.pc_url)
        process_event_booking_updates(form, self.pc, request)

        mock_messages.assert_called_once_with(request, 'Open booking for this user already exists')

    def test_full_class(self):
        baker.make_recipe('booking.booking', event=self.pc, _quantity=3)
        # fetch from db again b/c spaces left is cached
        pc = Event.objects.get(id=self.pc.id)
        self.assertEqual(pc.spaces_left, 0)
        resp = self.client.post(self.pc_url, {'user': self.user.id})
        form = resp.context_data['form']
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.non_field_errors(),
            ['Class is now full, booking could not be created. Please close this window and refresh register page.']
        )

    def test_full_event(self):
        baker.make_recipe('booking.booking', event=self.ev, _quantity=3)
        # fetch from db again b/c spaces left is cached
        ev = Event.objects.get(id=self.ev.id)
        self.assertEqual(ev.spaces_left, 0)
        resp = self.client.post(self.ev_url, {'user': self.user.id})
        form = resp.context_data['form']
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.non_field_errors(),
            ['Workshop is now full, booking could not be created. Please close this window and refresh register page.']
        )

    def test_remove_user_from_waiting_list(self):
        baker.make(WaitingListUser, user=self.user, event=self.pc)
        self.assertEqual(WaitingListUser.objects.count(), 1)

        self.client.post(self.pc_url, {'user': self.user.id})
        self.assertFalse(WaitingListUser.objects.exists())


class RegisterAjaxDisplayUpdateTests(TestPermissionMixin, TestCase):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.pc = baker.make_recipe('booking.future_PC', max_participants=3)

    def setUp(self):
        super().setUp()
        self.client.login(username=self.staff_user.username, password='test')
        self.booking = baker.make_recipe('booking.booking', user=self.user, event=self.pc)
        self.toggle_attended_url = reverse('studioadmin:ajax_toggle_attended', args=(self.booking.id,))

    def test_ajax_toggle_attended_get(self):
        # get not allowed
        resp = self.client.get(self.toggle_attended_url)
        self.assertEqual(resp.status_code, 405)

    def test_ajax_toggle_attended_no_data(self):
        resp = self.client.post(self.toggle_attended_url)
        self.assertEqual(resp.status_code, 400)

    def test_ajax_toggle_attended_bad_data(self):
        resp = self.client.post(self.toggle_attended_url, {'attendance': 'foo'})
        self.assertEqual(resp.status_code, 400)

    def test_ajax_toggle_attended(self):
        resp = self.client.post(self.toggle_attended_url,  {'attendance': 'attended'})
        self.assertTrue(resp.json()['attended'])
        self.assertIsNone(resp.json()['alert_msg'])

        self.booking.refresh_from_db()
        self.assertTrue(self.booking.attended)
        self.assertFalse(self.booking.no_show)

    def test_ajax_toggle_no_show(self):
        resp = self.client.post(self.toggle_attended_url, {'attendance': 'no-show'})
        self.assertFalse(resp.json()['attended'])
        self.assertIsNone(resp.json()['alert_msg'])

        self.booking.refresh_from_db()
        self.assertFalse(self.booking.attended)
        self.assertTrue(self.booking.no_show)

    @patch('booking.models.timezone')
    def test_ajax_toggle_no_show_outside_cancellation_period(self, mock_tz):
        mock_tz.now.return_value = datetime(2020, 3, 4, 18, 30, tzinfo=timezone.utc)
        # event > 24hrs in future
        self.booking.event.date = datetime(2020, 3, 7, 18, 30, tzinfo=timezone.utc)
        self.booking.event.save()
        self.client.post(self.toggle_attended_url, {'attendance': 'no-show'})
        self.booking.refresh_from_db()
        self.assertFalse(self.booking.attended)
        self.assertTrue(self.booking.no_show)
        self.assertFalse(self.booking.cancellation_fee_incurred)

    @patch('booking.models.timezone')
    def test_ajax_toggle_no_show_inside_cancellation_period(self, mock_tz):
        mock_tz.now.return_value = datetime(2020, 3, 4, 18, 30, tzinfo=timezone.utc)
        # event < 24hrs in future
        self.booking.event.date = datetime(2020, 3, 5, 17, 30, tzinfo=timezone.utc)
        self.booking.event.save()
        self.client.post(self.toggle_attended_url, {'attendance': 'no-show'})
        self.booking.refresh_from_db()
        self.assertFalse(self.booking.attended)
        self.assertTrue(self.booking.no_show)
        self.assertTrue(self.booking.cancellation_fee_incurred)
        self.assertFalse(self.booking.cancellation_fee_paid)

    def test_ajax_toggle_no_show_send_waiting_list_email_for_full_event(self):
        baker.make_recipe('booking.booking', event=self.pc, _quantity=2)
        pc = Event.objects.get(id=self.pc.id)
        self.assertEqual(pc.spaces_left, 0)
        baker.make(WaitingListUser, user__email="waitinglist@user.com", event=self.pc)

        self.client.post(self.toggle_attended_url, {'attendance': 'no-show'})
        self.booking.refresh_from_db()
        self.assertFalse(self.booking.attended)
        self.assertTrue(self.booking.no_show)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].bcc, ["waitinglist@user.com"])

    def test_ajax_toggle_no_show_no_waiting_list_email_for_full_event_within_30_mins(self):
        baker.make_recipe('booking.booking', event=self.pc, _quantity=2)
        pc = Event.objects.get(id=self.pc.id)
        self.assertEqual(pc.spaces_left, 0)
        baker.make(WaitingListUser, user__email="waitinglist@user.com", event=self.pc)

        pc.date = timezone.now() + timedelta(minutes=28)
        pc.save()
        self.client.post(self.toggle_attended_url, {'attendance': 'no-show'})
        self.booking.refresh_from_db()
        self.assertFalse(self.booking.attended)
        self.assertTrue(self.booking.no_show)
        # No waiting list email for events within 0.5 hr of current time
        self.assertEqual(len(mail.outbox), 0)

    def test_ajax_toggle_attended_cancelled_booking(self):
        self.booking.status = 'CANCELLED'
        self.booking.save()
        resp = self.client.post(self.toggle_attended_url, {'attendance': 'attended'})
        self.assertTrue(resp.json()['attended'])
        self.assertIsNone(resp.json()['alert_msg'])

        self.booking.refresh_from_db()
        self.assertTrue(self.booking.attended)
        self.assertFalse(self.booking.no_show)
        self.assertEqual(self.booking.status, 'OPEN')

    def test_ajax_toggle_attended_no_show_booking(self):
        self.booking.no_show = True
        self.booking.save()
        resp = self.client.post(self.toggle_attended_url, {'attendance': 'attended'})
        self.assertTrue(resp.json()['attended'])
        self.assertIsNone(resp.json()['alert_msg'])

        self.booking.refresh_from_db()
        self.assertTrue(self.booking.attended)
        self.assertFalse(self.booking.no_show)
        self.assertEqual(self.booking.status, 'OPEN')

    def test_ajax_toggle_attended_open_booking_full_event(self):
        baker.make_recipe('booking.booking', event=self.pc, _quantity=2)
        pc = Event.objects.get(id=self.pc.id)
        self.assertEqual(pc.spaces_left, 0)
        resp = self.client.post(self.toggle_attended_url, {'attendance': 'attended'})
        self.assertTrue(resp.json()['attended'])
        self.assertIsNone(resp.json()['alert_msg'])

        self.booking.refresh_from_db()
        self.assertTrue(self.booking.attended)
        self.assertFalse(self.booking.no_show)

    def test_ajax_toggle_attended_cancelled_booking_full_event(self):
        self.booking.status = 'CANCELLED'
        self.booking.save()
        baker.make_recipe('booking.booking', event=self.pc, _quantity=3)
        pc = Event.objects.get(id=self.pc.id)
        self.assertEqual(pc.spaces_left, 0)
        resp = self.client.post(self.toggle_attended_url, {'attendance': 'attended'})
        self.assertFalse(resp.json()['attended'])
        self.assertEqual(resp.json()['alert_msg'], 'Class is now full, cannot reopen booking.')

        self.booking.refresh_from_db()
        self.assertFalse(self.booking.attended)
        self.assertFalse(self.booking.no_show)

    def test_ajax_toggle_attended_no_show_booking_full_event(self):
        self.booking.no_show = True
        self.booking.save()
        baker.make_recipe('booking.booking', event=self.pc, _quantity=3)
        pc = Event.objects.get(id=self.pc.id)
        self.assertEqual(pc.spaces_left, 0)
        resp = self.client.post(self.toggle_attended_url, {'attendance': 'attended'})
        self.assertFalse(resp.json()['attended'])
        self.assertEqual(resp.json()['alert_msg'], 'Class is now full, cannot reopen booking.')

        self.booking.refresh_from_db()
        self.assertFalse(self.booking.attended)
        self.assertTrue(self.booking.no_show)


