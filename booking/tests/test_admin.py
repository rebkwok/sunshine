from model_mommy import mommy

from django import forms
from django.contrib.auth.models import User
from django.contrib.admin.sites import AdminSite
from django.test import TestCase
from django.urls import reverse

import booking.admin as admin
from booking.models import Event, Booking


class EventAdminTests(TestCase):

    def test_event_date_list_filter(self):
        mommy.make_recipe('booking.past_event', name='past')
        mommy.make_recipe('booking.future_EV', name='future')

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

        # no filter parameters returns all
        filter = admin.EventDateListFilter(None, {}, Event, admin.EventAdmin)
        events = filter.queryset(None, Event.objects.all())
        self.assertEqual(events.count(), 2)

    def test_spaces_left_display(self):
        event = mommy.make_recipe('booking.future_EV', max_participants=5)
        mommy.make_recipe('booking.booking', event=event, _quantity=3)

        ev_admin = admin.EventAdmin(Event, AdminSite())
        ev_query = ev_admin.get_queryset(None)[0]
        self.assertEqual(ev_admin.get_spaces_left(ev_query), 2)

    def test_booking_users_field_queryset(self):
        """
        Test that the user select in booking inline is filtered correctly
        For existing bookings, show only booked user
        For new bookings, exclude any users already booked
        """
        event = mommy.make_recipe('booking.future_EV', name='future')
        user1 = mommy.make(User, username='test1')
        mommy.make(User, _quantity=2)
        mommy.make_recipe('booking.booking', event=event, user=user1)

        superuser = User.objects.create_superuser(
            username='superuser', password='test', email='super@test.com'
        )
        self.client.login(username=superuser.username, password='test')
        resp = self.client.get(
            reverse('admin:booking_event_change', args=[event.id])
        )

        booked_form = resp.context_data['inline_admin_formsets'][0] \
            .formset.forms[0]
        self.assertEqual(booked_form.fields['user'].queryset.count(), 1)
        self.assertEqual(
            list(booked_form.fields['user'].queryset),
            list(User.objects.filter(id=user1.id))
        )
        new_form = resp.context_data['inline_admin_formsets'][0] \
            .formset.forms[1]
        self.assertEqual(new_form.fields['user'].queryset.count(), 3)
        self.assertEqual(
            list(new_form.fields['user'].queryset),
            list(User.objects.exclude(id=user1.id))
        )

    def test_booking_inline_delete_display(self):
        """
        Only show the delete checkbox for unpaid bookings
        """
        event = mommy.make_recipe('booking.future_EV', name='future')
        mommy.make_recipe('booking.booking', event=event, paid=False)
        mommy.make_recipe('booking.booking', event=event, paid=True)

        superuser = User.objects.create_superuser(
            username='superuser', password='test', email='super@test.com'
        )
        self.client.login(username=superuser.username, password='test')
        resp = self.client.get(
            reverse('admin:booking_event_change', args=[event.id])
        )

        paid_form = resp.context_data['inline_admin_formsets'][0] \
            .formset.forms[0]
        unpaid_form = resp.context_data['inline_admin_formsets'][0] \
            .formset.forms[1]
        self.assertIsInstance(paid_form.fields['DELETE'].widget, forms.CheckboxInput)
        self.assertIsInstance(unpaid_form.fields['DELETE'].widget, forms.HiddenInput)

    def test_creating_new_booking(self):
        event = mommy.make_recipe('booking.future_EV', name='future')
        user1 = mommy.make(User, username='test1')
        mommy.make(User, _quantity=2)

        superuser = User.objects.create_superuser(
            username='superuser', password='test', email='super@test.com'
        )
        self.client.login(username=superuser.username, password='test')
        self.assertFalse(event.bookings.exists())

        form_data = {
            'name': event.name,
            'date_0': event.date.strftime('%d/%m/%Y'),
            'date_1': event.date.strftime('%H:%M'),
            'location': event.location,
            'event_type': event.event_type,
            'max_participants': event.max_participants,
            'description': event.description,
            'contact_email': event.contact_email,
            'email_studio_when_booked': event.email_studio_when_booked,
            'cost': event.cost,
            'paypal_email': event.paypal_email,
            'allow_booking_cancellation': event.allow_booking_cancellation,
            'cancellation_period': event.cancellation_period,
            'show_on_site': event.show_on_site,
            'bookings-INITIAL_FORMS': 0,
            'bookings-TOTAL_FORMS': 1,
            'bookings-0-user': user1.id,
            'bookings-0-paid': False,
            'bookings-0-status': 'OPEN'
        }
        self.client.post(
            reverse('admin:booking_event_change', args=[event.id]),
            form_data
        )

        self.assertEqual(event.bookings.count(), 1)
        self.assertEqual(event.bookings.first().user, user1)


class BookingAdminTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = mommy.make_recipe(
            'booking.user', first_name="Test", last_name="User",
            username="testuser"
        )

    def test_booking_date_list_filter(self):
        past_event = mommy.make_recipe('booking.past_event', name='past')
        future_event = mommy.make_recipe('booking.future_EV', name='future')
        mommy.make_recipe('booking.booking', user=self.user, event=past_event)
        mommy.make_recipe('booking.booking', user=self.user, event=future_event)

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
        event = mommy.make_recipe('booking.future_EV', cost=6)

        booking = mommy.make_recipe(
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
        user = mommy.make_recipe(
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
        user = mommy.make_recipe(
            'booking.user', first_name='Donald', last_name='Duck',
            username='dd')
        mommy.make_recipe('booking.booking', user=self.user, _quantity=5)
        mommy.make_recipe('booking.booking', user=user, _quantity=5)

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
