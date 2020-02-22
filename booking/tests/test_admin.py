from datetime import timedelta, datetime
from unittest.mock import Mock

from model_bakery import baker

from django.core import mail
from django.contrib.auth.models import User
from django.contrib.admin.sites import AdminSite
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

import booking.admin as admin
from booking.models import Event, Booking, Workshop, RegularClass, Register


class EventAdminTests(TestCase):

    def test_event_date_list_filter(self):
        baker.make_recipe('booking.past_event', name='past')
        baker.make_recipe('booking.future_EV', name='future')

        filter = admin.EventDateListFilter(
            None, {'date': 'past'}, Event, admin.EventAdmin
        )
        event = filter.queryset(None, Event.objects.all())[0]
        self.assertEqual(event.name, 'past')

        filter = admin.EventDateListFilter(
            None, {'date': 'upcoming'}, Event, admin.EventAdmin
        )
        event = filter.queryset(None, Event.objects.all())[0]
        self.assertEqual(event.name, 'future')

    def test_get_cancelled_status_display(self):
        event = baker.make_recipe('booking.future_EV')
        ev_admin = admin.EventAdmin(Event, AdminSite())
        ev_query = ev_admin.get_queryset(None)[0]
        self.assertEqual(ev_admin.status(ev_query), 'OPEN')

        event.cancelled = True
        event.save()
        ev_query = ev_admin.get_queryset(None)[0]
        self.assertEqual(ev_admin.status(ev_query), 'CANCELLED')

    def test_spaces_left_display(self):
        event = baker.make_recipe('booking.future_EV', max_participants=5)
        baker.make_recipe('booking.booking', event=event, _quantity=3)

        ev_admin = admin.EventAdmin(Event, AdminSite())
        ev_query = ev_admin.get_queryset(None)[0]
        self.assertEqual(ev_admin.get_spaces_left(ev_query), 2)

    def test_event_date_display(self):
        event = baker.make_recipe('booking.future_EV', date=datetime(2019, 1, 23, 18, 0, tzinfo=timezone.utc))
        baker.make_recipe('booking.booking', event=event, _quantity=3)

        ev_admin = admin.EventAdmin(Event, AdminSite())
        ev_query = ev_admin.get_queryset(None)[0]
        self.assertEqual(ev_admin.get_date(ev_query), 'Wed 23 Jan 2019 18:00 (GMT)')

        # BST datetime
        event.date = datetime(2019, 7, 23, 17, 0, tzinfo=timezone.utc)
        event.save()
        ev_query = ev_admin.get_queryset(None)[0]
        self.assertEqual(ev_admin.get_date(ev_query), 'Tue 23 Jul 2019 18:00 (BST)')

    def test_cancel_event_action(self):
        event = baker.make_recipe('booking.future_EV', max_participants=5)
        for i in range(3):
            baker.make_recipe('booking.booking', event=event, user__email='test{}@test.test'.format(i))
        self.assertEqual(event.bookings.filter(status='OPEN').count(), 3)

        ev_admin = admin.EventAdmin(Event, AdminSite())
        request = Mock()
        ev_admin.cancel_event(request, Event.objects.filter(id=event.id))
        event.refresh_from_db()
        self.assertTrue(event.cancelled)
        for booking in event.bookings.all():
            self.assertEqual(booking.status, 'CANCELLED')

        # emails sent to 3 open bookings
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(len(mail.outbox[0].bcc), 3)

    def test_cancel_event_action_cancelled_bookings(self):
        event = baker.make_recipe('booking.future_EV', max_participants=5)
        for i in range(3):
            baker.make_recipe('booking.booking', event=event, user__email='test{}@test.test'.format(i))
        baker.make_recipe('booking.booking', event=event, no_show=True, user__email='test3@test.test')
        baker.make_recipe('booking.booking', event=event, status='CANCELLED', user__email='test4@test.test')

        ev_admin = admin.EventAdmin(Event, AdminSite())
        request = Mock()
        ev_admin.cancel_event(request, Event.objects.filter(id=event.id))
        event.refresh_from_db()
        self.assertTrue(event.cancelled)

        self.assertEqual(event.bookings.filter(status='CANCELLED').count(), 4)
        self.assertEqual(event.bookings.filter(status='OPEN', no_show=True).count(), 1)

        # emails sent to 3 open bookings
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(len(mail.outbox[0].bcc), 3)

    def test_cancel_event_action_cancelled_bookings_only(self):
        event = baker.make_recipe('booking.future_EV', max_participants=5)
        baker.make_recipe('booking.booking', event=event, no_show=True, user__email='test3@test.test')
        baker.make_recipe('booking.booking', event=event, status='CANCELLED', user__email='test4@test.test')
        self.assertEqual(event.bookings.filter(status='OPEN', no_show=False).count(), 0)

        ev_admin = admin.EventAdmin(Event, AdminSite())
        request = Mock()
        ev_admin.cancel_event(request, Event.objects.filter(id=event.id))
        event.refresh_from_db()
        self.assertTrue(event.cancelled)

        # no emails sent
        self.assertEqual(len(mail.outbox), 0)

    def test_cancel_event_action_no_bookings(self):
        event = baker.make_recipe('booking.future_EV', max_participants=5)
        self.assertEqual(event.bookings.filter(status='OPEN').count(), 0)

        ev_admin = admin.EventAdmin(Event, AdminSite())
        request = Mock()
        ev_admin.cancel_event(request, Event.objects.filter(id=event.id))
        self.assertFalse(Event.objects.exists())

        # no emails sent
        self.assertEqual(len(mail.outbox), 0)

    def test_cannot_cancel_past_event_with_booking(self):
        event = baker.make_recipe('booking.past_event')
        baker.make_recipe('booking.booking', event=event, user__email='test@test.test')

        ev_admin = admin.EventAdmin(Event, AdminSite())
        request = Mock()
        ev_admin.cancel_event(request, Event.objects.filter(id=event.id))
        event.refresh_from_db()
        self.assertFalse(event.cancelled)

        # no emails sent
        self.assertEqual(len(mail.outbox), 0)

    def test_cannot_cancel_past_event_with_cancelled_booking(self):
        event = baker.make_recipe('booking.past_event')
        baker.make_recipe('booking.booking', event=event, user__email='test@test.test', status='CANCELLED')

        ev_admin = admin.EventAdmin(Event, AdminSite())
        request = Mock()
        ev_admin.cancel_event(request, Event.objects.filter(id=event.id))
        event.refresh_from_db()
        self.assertFalse(event.cancelled)

        # no emails sent
        self.assertEqual(len(mail.outbox), 0)

    def test_actions(self):
        # only cancel_event action, no delete option
        ev_admin = admin.EventAdmin(Event, AdminSite())
        request = Mock(GET=[])
        actions = ev_admin.get_actions(request)
        self.assertEqual(list(actions.keys()), ['cancel_event'])

    def test_form_venue_not_deleteable(self):
        event = baker.make_recipe('booking.future_EV', max_participants=5)
        ev_admin = admin.EventAdmin(Event, AdminSite())
        request = Mock()
        form = ev_admin.get_form(request, obj=event)
        self.assertFalse(form.base_fields['venue'].widget.can_delete_related)


class EventProxyAdminTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.workshops = baker.make_recipe('booking.future_EV', _quantity=2)
        cls.regularclasses = baker.make_recipe('booking.future_PC', _quantity=3)

    def test_queryset_workshops(self):
        workshop_admin = admin.WorkshopAdmin(Workshop, AdminSite())
        self.assertEqual(workshop_admin.get_queryset(None).count(), 2)

    def test_queryset_regular_sessions(self):
        class_admin = admin.RegularClassAdmin(RegularClass, AdminSite())
        self.assertEqual(class_admin.get_queryset(None).count(), 3)

    def test_form_cost_help_text(self):
        # cost help text on workshop only
        ws_admin = admin.WorkshopAdmin(Workshop, AdminSite())
        request = Mock()
        form = ws_admin.get_form(request, obj=self.workshops[0])
        self.assertEqual(form.base_fields['cost'].help_text, '')

        regclass_admin = admin.RegularClassAdmin(RegularClass, AdminSite())
        request = Mock()
        form = regclass_admin.get_form(request, obj=self.regularclasses[0])
        self.assertEqual(form.base_fields['cost'].help_text, '(non-membership cost)')

    def test_status_labels(self):
        superuser = User.objects.create_superuser(
            username='superuser', password='test', email='super@test.com'
        )
        self.client.login(username=superuser.username, password='test')
        resp = self.client.get(reverse('admin:booking_workshop_changelist'))
        self.assertIn('Workshop Status', resp.rendered_content)
        self.assertNotIn('Class Status', resp.rendered_content)
        self.assertNotIn('Event Status', resp.rendered_content)

        resp = self.client.get(reverse('admin:booking_regularclass_changelist'))
        self.assertIn('Class Status', resp.rendered_content)
        self.assertNotIn('Workshop Status', resp.rendered_content)
        self.assertNotIn('Event Status', resp.rendered_content)

    def test_cancel_labels(self):
        superuser = User.objects.create_superuser(
            username='superuser', password='test', email='super@test.com'
        )
        self.client.login(username=superuser.username, password='test')
        resp = self.client.get(reverse('admin:booking_workshop_change', args=[self.workshops[0].id]))
        self.assertIn('Cancel workshop', resp.rendered_content)
        self.assertNotIn('Cancel class', resp.rendered_content)
        self.assertNotIn('Cancel event', resp.rendered_content)

        resp = self.client.get(reverse('admin:booking_regularclass_change', args=[self.regularclasses[0].id]))
        self.assertIn('Cancel class', resp.rendered_content)
        self.assertNotIn('Cancel workshop', resp.rendered_content)
        self.assertNotIn('Cancel event', resp.rendered_content)

    def test_cancel_workshop_action(self):
        event = baker.make_recipe('booking.future_EV', max_participants=5)
        for i in range(3):
            baker.make_recipe('booking.booking', event=event, user__email='test{}@test.test'.format(i))
        self.assertEqual(event.bookings.filter(status='OPEN').count(), 3)

        ev_admin = admin.WorkshopAdmin(Workshop, AdminSite())
        request = Mock()
        ev_admin.cancel_event(request, Workshop.objects.filter(id=event.id))
        event.refresh_from_db()
        self.assertTrue(event.cancelled)
        for booking in event.bookings.all():
            self.assertEqual(booking.status, 'CANCELLED')

        # emails sent to 3 open bookings
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(len(mail.outbox[0].bcc), 3)

    def test_cancel_event_action(self):
        event = baker.make_recipe('booking.future_PC', max_participants=5)
        for i in range(3):
            baker.make_recipe('booking.booking', event=event, user__email='test{}@test.test'.format(i))
        self.assertEqual(event.bookings.filter(status='OPEN').count(), 3)

        ev_admin = admin.RegularClassAdmin(RegularClass, AdminSite())
        request = Mock()
        ev_admin.cancel_event(request, RegularClass.objects.filter(id=event.id))
        event.refresh_from_db()
        self.assertTrue(event.cancelled)
        for booking in event.bookings.all():
            self.assertEqual(booking.status, 'CANCELLED')

        # emails sent to 3 open bookings
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(len(mail.outbox[0].bcc), 3)


class RegisterAdminTests(TestCase):

    def test_creating_new_booking(self):
        event = baker.make_recipe('booking.future_EV', name='future')
        user1 = baker.make(User, username='test1')
        baker.make(User, _quantity=2)

        superuser = User.objects.create_superuser(
            username='superuser', password='test', email='super@test.com'
        )
        self.client.login(username=superuser.username, password='test')
        self.assertFalse(event.bookings.exists())

        form_data = {
            'bookings-INITIAL_FORMS': 0,
            'bookings-TOTAL_FORMS': 1,
            'bookings-0-user': user1.id,
            'bookings-0-paid': False,
            'bookings-0-status': 'OPEN',
            'waitinglistusers-INITIAL_FORMS': 0,
            'waitinglistusers-TOTAL_FORMS': 0,
        }
        self.client.post(
            reverse('admin:booking_register_change', args=[event.id]),
            form_data
        )

        self.assertEqual(event.bookings.count(), 1)
        self.assertEqual(event.bookings.first().user, user1)

    def test_spaces_left_display(self):
        event = baker.make_recipe('booking.future_EV', max_participants=5)
        baker.make_recipe('booking.booking', event=event, _quantity=3)

        reg_admin = admin.RegisterAdmin(Register, AdminSite())
        reg_query = reg_admin.get_queryset(None)[0]
        self.assertEqual(reg_admin.get_spaces_left(reg_query), 2)

    def test_event_date_display(self):
        event = baker.make_recipe('booking.future_EV', date=datetime(2019, 1, 23, 18, 0, tzinfo=timezone.utc))
        baker.make_recipe('booking.booking', event=event, _quantity=3)

        reg_admin = admin.RegisterAdmin(Register, AdminSite())
        reg_query = reg_admin.get_queryset(None)[0]
        self.assertEqual(reg_admin.get_date(reg_query), 'Wed 23 Jan 2019 18:00 (GMT)')

    def test_actions(self):
        # no delete option
        ev_admin = admin.RegisterAdmin(Register, AdminSite())
        request = Mock(GET=[])
        actions = ev_admin.get_actions(request)
        self.assertEqual(list(actions.keys()), [])


class BookingAdminTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = baker.make_recipe(
            'booking.user', first_name="Test", last_name="User",
            username="testuser"
        )

    def test_booking_date_list_filter(self):
        past_event = baker.make_recipe('booking.past_event', name='past')
        future_event = baker.make_recipe('booking.future_EV', name='future')
        baker.make_recipe('booking.booking', user=self.user, event=past_event)
        baker.make_recipe('booking.booking', user=self.user, event=future_event)

        filter = admin.BookingDateListFilter(
            None, {'event__date': 'past'}, Booking, admin.BookingAdmin
        )
        booking = filter.queryset(None, Booking.objects.all())[0]
        self.assertEqual(booking.event.name, 'past')

        filter = admin.BookingDateListFilter(
            None, {'event__date': 'upcoming'}, Booking, admin.BookingAdmin
        )
        booking = filter.queryset(None, Booking.objects.all())[0]
        self.assertEqual(booking.event.name, 'future')

        # no filter parameters returns all
        filter = admin.BookingDateListFilter(
            None, {}, Booking, admin.BookingAdmin
        )
        bookings = filter.queryset(None, Booking.objects.all())
        self.assertEqual(bookings.count(), 2)

    def test_booking_admin_display(self):
        event = baker.make_recipe('booking.future_EV', cost=6)

        booking = baker.make_recipe(
            'booking.booking', user=self.user, event=event
        )

        booking_admin = admin.BookingAdmin(Booking, AdminSite())
        booking_query = booking_admin.get_queryset(None)[0]

        self.assertEqual(
            booking_admin.get_date(booking_query), booking.event.date
        )
        self.assertEqual(
            booking_admin.get_user(booking_query), 'Test User (testuser)'
        )
        self.assertEqual(
            booking_admin.get_cost(booking_query),
            u"\u00A3{}.00".format(event.cost)
        )
        self.assertEqual(booking_admin.event_name(booking_query), event.name)

    def test_booking_user_filter_choices(self):
        # test that user filter shows formatted choices ordered by first name
        user = baker.make_recipe(
            'booking.user', first_name='Donald', last_name='Duck',
            username='dd')
        userfilter = admin.UserFilter(None, {}, Booking, admin.BookingAdmin)
        self.assertEqual(
            userfilter.lookup_choices,
            [
                (user.id, 'Donald Duck (dd)'),
                (self.user.id, 'Test User (testuser)')
            ]
        )

    def test_booking_user_filter(self):
        user = baker.make_recipe(
            'booking.user', first_name='Donald', last_name='Duck',
            username='dd')
        baker.make_recipe('booking.booking', user=self.user, _quantity=5)
        baker.make_recipe('booking.booking', user=user, _quantity=5)

        userfilter = admin.UserFilter(None, {}, Booking, admin.BookingAdmin)
        result = userfilter.queryset(None, Booking.objects.all())

        # with no filter parameters, return all
        self.assertEqual(Booking.objects.count(), 10)
        self.assertEqual(result.count(), 10)
        self.assertEqual(
            [booking.id for booking in result],
            [booking.id for booking in Booking.objects.all()]
        )

        userfilter = admin.UserFilter(
            None, {'user': self.user.id}, Booking, admin.BookingAdmin
        )
        result = userfilter.queryset(None, Booking.objects.all())
        self.assertEqual(result.count(), 5)
        self.assertEqual(
            [booking.id for booking in result],
            [booking.id for booking in Booking.objects.filter(user=self.user)]
        )
