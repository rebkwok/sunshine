from datetime import timedelta, datetime
from unittest.mock import Mock, patch

import pytest
from model_bakery import baker

from django.core import mail
from django.contrib.auth.models import User
from django.contrib.admin.sites import AdminSite
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

import booking.admin as admin
from booking.email_helpers import email_waiting_lists
from booking.models import Event, Booking, GiftVoucher, ItemVoucher, MembershipType, Private, TotalVoucher, Workshop, RegularClass
from stripe_payments.models import Invoice, StripeRefund


class EventAdminTests(TestCase):

    def test_event_date_list_filter(self):
        baker.make_recipe('booking.past_event', name='past')
        baker.make_recipe('booking.future_EV', name='future')

        filter = admin.EventDateListFilter(
            None, {'date': 'past'}, Event, admin.EventAdmin
        )
        event = filter.queryset(None, Event.objects.all())[0]
        assert event.name == 'past'

        # default value
        filter = admin.EventDateListFilter(
            None, {'date': None}, Event, admin.EventAdmin
        )
        events = filter.queryset(None, Event.objects.all())
        assert len(events), 1
        event = events[0]
        assert event.name == 'future'

        filter = admin.EventDateListFilter(
            None, {}, Event, admin.EventAdmin
        )
        event = filter.queryset(None, Event.objects.all())[0]
        assert event.name == 'future'

        filter = admin.EventDateListFilter(
            None, {'date': "all"}, Event, admin.EventAdmin
        )
        events = filter.queryset(None, Event.objects.all())
        assert len(events) == 2

    def test_get_cancelled_status_display(self):
        event = baker.make_recipe('booking.future_EV')
        ev_admin = admin.EventAdmin(Event, AdminSite())
        ev_query = ev_admin.get_queryset(None)[0]
        assert ev_admin.status(ev_query) == 'OPEN'

        event.cancelled = True
        event.save()
        ev_query = ev_admin.get_queryset(None)[0]
        assert ev_admin.status(ev_query) == 'CANCELLED'

    def test_spaces_left_display(self):
        event = baker.make_recipe('booking.future_EV', max_participants=5)
        baker.make_recipe('booking.booking', event=event, _quantity=3)

        ev_admin = admin.EventAdmin(Event, AdminSite())
        ev_query = ev_admin.get_queryset(None)[0]
        assert ev_admin.get_spaces_left(ev_query) == 2

    def test_event_date_display(self):
        event = baker.make_recipe('booking.future_EV', date=datetime(2019, 1, 23, 18, 0, tzinfo=timezone.utc))
        baker.make_recipe('booking.booking', event=event, _quantity=3)

        ev_admin = admin.EventAdmin(Event, AdminSite())
        ev_query = ev_admin.get_queryset(None)[0]
        assert ev_admin.get_date(ev_query) == 'Wed 23 Jan 2019 18:00 (GMT)'

        # BST datetime
        event.date = datetime(2019, 7, 23, 17, 0, tzinfo=timezone.utc)
        event.save()
        ev_query = ev_admin.get_queryset(None)[0]
        assert ev_admin.get_date(ev_query) == 'Tue 23 Jul 2019 18:00 (BST)'

    def test_cancel_event_action(self):
        event = baker.make_recipe('booking.future_EV', max_participants=5)
        for i in range(3):
            baker.make_recipe('booking.booking', event=event, user__email='test{}@test.test'.format(i), paid=True)
        assert event.bookings.filter(status='OPEN').count() == 3

        ev_admin = admin.EventAdmin(Event, AdminSite())
        request = Mock()
        ev_admin.cancel_event(request, Event.objects.filter(id=event.id))
        event.refresh_from_db()
        assert event.cancelled
        for booking in event.bookings.all():
            assert booking.status == 'CANCELLED'

        # emails sent to 3 open bookings
        assert len(mail.outbox) ==  3

    def test_cancel_event_action_booking_with_membership(self):
        event = baker.make_recipe('booking.future_EV', max_participants=5)
        membership = baker.make_recipe('booking.membership', paid=True, user__email='member@test.test')
        membership_booking = baker.make_recipe(
            'booking.booking', event=event, user=membership.user, 
            membership=membership, paid=True
        )
        assert membership_booking.membership == membership
        assert event.bookings.filter(status='OPEN').count() == 1

        ev_admin = admin.EventAdmin(Event, AdminSite())
        request = Mock()
        ev_admin.cancel_event(request, Event.objects.filter(id=event.id))
        event.refresh_from_db()
        assert event.cancelled

        # emails sent to 1 open booking
        assert len(mail.outbox) == 1
        email = mail.outbox[0]
        assert email.to == ['member@test.test']
        assert "Credit for this Workshop has been returned to your membership" in email.body
        membership_booking.refresh_from_db()
        assert membership_booking.status == 'CANCELLED'
        assert not membership_booking.paid
        assert membership_booking.membership is None

    @patch("booking.admin.process_refund")
    def test_cancel_event_action_booking_with_stripe(self, mock_process_refund):
        mock_process_refund.return_value = True

        event = baker.make_recipe('booking.future_EV', max_participants=5)
        invoice = baker.make(
            Invoice, paid=True, username='member@test.test',
            invoice_id="inv123",
            stripe_payment_intent_id="pi_123"
        )
        booking = baker.make_recipe(
            'booking.booking', event=event, user__email=invoice.username, 
            paid=True, invoice=invoice
        )
        assert event.bookings.filter(status='OPEN').count() == 1

        ev_admin = admin.EventAdmin(Event, AdminSite())
        request = Mock()
        ev_admin.cancel_event(request, Event.objects.filter(id=event.id))
        event.refresh_from_db()
        assert event.cancelled

        # emails sent to 1 open booking
        assert len(mail.outbox) == 1
        email = mail.outbox[0]
        assert email.to == ['member@test.test']
        assert "Your refund for this Workshop is being processed" in email.body
        booking.refresh_from_db()
        assert booking.status == 'CANCELLED'
        assert not booking.paid
        assert booking.membership is None

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
        assert event.cancelled

        assert event.bookings.filter(status='CANCELLED').count() == 4
        assert event.bookings.filter(status='OPEN', no_show=True).count() == 1

        # emails sent to 3 open bookings
        assert len(mail.outbox) == 3

    def test_cancel_event_action_cancelled_bookings_only(self):
        event = baker.make_recipe('booking.future_EV', max_participants=5)
        baker.make_recipe('booking.booking', event=event, no_show=True, user__email='test3@test.test')
        baker.make_recipe('booking.booking', event=event, status='CANCELLED', user__email='test4@test.test')
        assert event.bookings.filter(status='OPEN', no_show=False).count() == 0

        ev_admin = admin.EventAdmin(Event, AdminSite())
        request = Mock()
        ev_admin.cancel_event(request, Event.objects.filter(id=event.id))
        event.refresh_from_db()
        assert event.cancelled

        # no emails sent
        assert len(mail.outbox) == 0

    def test_cancel_event_action_no_bookings(self):
        event = baker.make_recipe('booking.future_EV', max_participants=5)
        assert event.bookings.filter(status='OPEN').count() == 0

        ev_admin = admin.EventAdmin(Event, AdminSite())
        request = Mock()
        ev_admin.cancel_event(request, Event.objects.filter(id=event.id))
        assert not Event.objects.exists()

        # no emails sent
        assert len(mail.outbox) == 0

    def test_cannot_cancel_past_event_with_booking(self):
        event = baker.make_recipe('booking.past_event')
        baker.make_recipe('booking.booking', event=event, user__email='test@test.test')

        ev_admin = admin.EventAdmin(Event, AdminSite())
        request = Mock()
        ev_admin.cancel_event(request, Event.objects.filter(id=event.id))
        event.refresh_from_db()
        assert not event.cancelled

        # no emails sent
        assert len(mail.outbox) == 0

    def test_cannot_cancel_past_event_with_cancelled_booking(self):
        event = baker.make_recipe('booking.past_event')
        baker.make_recipe('booking.booking', event=event, user__email='test@test.test', status='CANCELLED')

        ev_admin = admin.EventAdmin(Event, AdminSite())
        request = Mock()
        ev_admin.cancel_event(request, Event.objects.filter(id=event.id))
        event.refresh_from_db()
        assert not event.cancelled

        # no emails sent
        assert len(mail.outbox) == 0

    def test_actions(self):
        # only cancel_event action, no delete option
        ev_admin = admin.EventAdmin(Event, AdminSite())
        request = Mock(GET=[])
        actions = ev_admin.get_actions(request)
        assert list(actions.keys()) == ['cancel_event']

    def test_form_venue_not_deleteable(self):
        event = baker.make_recipe('booking.future_EV', max_participants=5)
        ev_admin = admin.EventAdmin(Event, AdminSite())
        request = Mock()
        form = ev_admin.get_form(request, obj=event)
        assert not form.base_fields['venue'].widget.can_delete_related


class EventProxyAdminTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.workshops = baker.make_recipe('booking.future_EV', _quantity=2)
        cls.regularclasses = baker.make_recipe('booking.future_PC', _quantity=3)
        cls.privates = baker.make_recipe('booking.future_PV', _quantity=4)

    def test_queryset_workshops(self):
        workshop_admin = admin.WorkshopAdmin(Workshop, AdminSite())
        assert workshop_admin.get_queryset(None).count() == 2

    def test_queryset_regular_sessions(self):
        class_admin = admin.RegularClassAdmin(RegularClass, AdminSite())
        assert class_admin.get_queryset(None).count() == 3

    def test_queryset_privates(self):
        private_admin = admin.PrivateAdmin(Private, AdminSite())
        assert private_admin.get_queryset(None).count() == 4

    def test_form_cost_help_text(self):
        # cost help text on workshop only
        ws_admin = admin.WorkshopAdmin(Workshop, AdminSite())
        request = Mock()
        form = ws_admin.get_form(request, obj=self.workshops[0])
        assert form.base_fields['cost'].help_text == ''

        regclass_admin = admin.RegularClassAdmin(RegularClass, AdminSite())
        request = Mock()
        form = regclass_admin.get_form(request, obj=self.regularclasses[0])
        assert form.base_fields['cost'].help_text == '(non-membership cost)'

        private_admin = admin.PrivateAdmin(Private, AdminSite())
        request = Mock()
        form = private_admin.get_form(request, obj=self.privates[0])
        assert form.base_fields['cost'].help_text == ''

    def test_status_labels(self):
        superuser = User.objects.create_superuser(
            username='superuser', password='test', email='super@test.com'
        )
        self.client.login(username=superuser.username, password='test')
        resp = self.client.get(reverse('admin:booking_workshop_changelist'))
        assert 'Workshop Status'in resp.rendered_content
        assert 'Class Status' not in resp.rendered_content
        assert 'Event Status' not in resp.rendered_content

        resp = self.client.get(reverse('admin:booking_regularclass_changelist'))
        assert 'Class Status' in resp.rendered_content
        assert 'Workshop Status' not in  resp.rendered_content
        assert 'Event Status' not in  resp.rendered_content

        resp = self.client.get(reverse('admin:booking_private_changelist'))
        assert 'Class Status'in resp.rendered_content
        assert 'Workshop Status' not in  resp.rendered_content
        assert 'Event Status' not in resp.rendered_content

    def test_cancel_labels(self):
        superuser = User.objects.create_superuser(
            username='superuser', password='test', email='super@test.com'
        )
        self.client.login(username=superuser.username, password='test')
        resp = self.client.get(reverse('admin:booking_workshop_change', args=[self.workshops[0].id]))
        assert 'Cancel workshop' in resp.rendered_content
        assert 'Cancel class' not in  resp.rendered_content
        assert 'Cancel event' not in  resp.rendered_content

        resp = self.client.get(reverse('admin:booking_regularclass_change', args=[self.regularclasses[0].id]))
        assert 'Cancel class' in resp.rendered_content
        assert 'Cancel workshop' not in  resp.rendered_content
        assert 'Cancel event' not in  resp.rendered_content

        resp = self.client.get(reverse('admin:booking_private_change', args=[self.privates[0].id]))
        assert 'Cancel class' in  resp.rendered_content
        assert 'Cancel workshop' not in resp.rendered_content
        assert 'Cancel event' not in  resp.rendered_content

    def test_cancel_workshop_action(self):
        event = baker.make_recipe('booking.future_EV', max_participants=5)
        for i in range(3):
            baker.make_recipe('booking.booking', event=event, user__email='test{}@test.test'.format(i))
        assert event.bookings.filter(status='OPEN').count() == 3

        ev_admin = admin.WorkshopAdmin(Workshop, AdminSite())
        request = Mock()
        ev_admin.cancel_event(request, Workshop.objects.filter(id=event.id))
        event.refresh_from_db()
        assert event.cancelled
        for booking in event.bookings.all():
            assert booking.status == 'CANCELLED'

        # emails sent to 3 open bookings
        assert len(mail.outbox) == 3

    def test_cancel_event_action(self):
        event = baker.make_recipe('booking.future_PC', max_participants=5)
        for i in range(3):
            baker.make_recipe('booking.booking', event=event, user__email='test{}@test.test'.format(i))
        assert event.bookings.filter(status='OPEN').count() == 3

        ev_admin = admin.RegularClassAdmin(RegularClass, AdminSite())
        request = Mock()
        ev_admin.cancel_event(request, RegularClass.objects.filter(id=event.id))
        event.refresh_from_db()
        assert event.cancelled
        for booking in event.bookings.all():
            assert booking.status == 'CANCELLED'

        # emails sent to 3 open bookings
        assert len(mail.outbox) == 3

    def test_cancel_private_action(self):
        event = baker.make_recipe('booking.future_PV', max_participants=5)
        for i in range(3):
            baker.make_recipe('booking.booking', event=event, user__email='test{}@test.test'.format(i))
        assert event.bookings.filter(status='OPEN').count() == 3

        ev_admin = admin.PrivateAdmin(Private, AdminSite())
        request = Mock()
        ev_admin.cancel_event(request, Private.objects.filter(id=event.id))
        event.refresh_from_db()
        assert event.cancelled
        for booking in event.bookings.all():
            assert booking.status == 'CANCELLED'

        # emails sent to 3 open bookings
        assert len(mail.outbox) == 3

    def test_regular_class_actions(self):
        # only cancel_event action, no delete option
        ev_admin = admin.RegularClassAdmin(RegularClass, AdminSite())
        request = Mock(GET=[])
        actions = ev_admin.get_actions(request)
        assert list(actions.keys()) == ['cancel_event', "toggle_members_only"]

    def test_toggle_members_only_action(self):
        event = baker.make_recipe('booking.future_PC', max_participants=5, members_only=False)
        event1 = baker.make_recipe('booking.future_PC', max_participants=5, members_only=True)
        event2 = baker.make_recipe('booking.future_PC', max_participants=5, members_only=True)

        ev_admin = admin.RegularClassAdmin(RegularClass, AdminSite())
        request = Mock()
        ev_admin.toggle_members_only(request, RegularClass.objects.filter(id__in=[event.id, event1.id]))
        for ev in [event, event1, event2]:
            ev.refresh_from_db()

        # event and event1 have been toggle
        assert event.members_only
        assert not event1.members_only
        # event2 has not been toggled
        assert event2.members_only


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

        datefilter = admin.BookingDateListFilter(
            None, {'event__date': 'past'}, Booking, admin.BookingAdmin
        )
        booking = datefilter.queryset(None, Booking.objects.all())[0]
        assert booking.event.name == 'past'

        # no filter parameters returns default (upcoming)
        datefilter = admin.BookingDateListFilter(
            None, {'event__date': None}, Booking, admin.BookingAdmin
        )
        booking = datefilter.queryset(None, Booking.objects.all())[0]
        assert booking.event.name == 'future'

        datefilter = admin.BookingDateListFilter(
            None, {'event__date': 'all'}, Booking, admin.BookingAdmin
        )
        bookings = datefilter.queryset(None, Booking.objects.all())
        assert bookings.count() == 2

    def test_booking_admin_display(self):
        event = baker.make_recipe('booking.future_EV', cost=6)

        booking = baker.make_recipe(
            'booking.booking', user=self.user, event=event, paid=True
        )

        booking_admin = admin.BookingAdmin(Booking, AdminSite())
        booking_query = booking_admin.get_queryset(None)[0]
        
        assert booking_admin.event_name(booking_query) == booking.event.name
        assert booking_admin.get_date(booking_query) == booking.event.date
        assert booking_admin.get_user(booking_query) == 'Test User (testuser)'
        assert booking_admin.get_cost(booking_query) == u"\u00A3{}.00".format(event.cost)
        assert booking_admin.refunded(booking_query) == "-"

        baker.make(StripeRefund, booking_id=booking.id)
        assert booking_admin.refunded(booking_query)

    def test_booking_user_filter_choices(self):
        # test that user filter shows formatted choices ordered by first name
        user = baker.make_recipe(
            'booking.user', first_name='Donald', last_name='Duck',
            username='dd')
        userfilter = admin.UserFilter(None, {}, Booking, admin.BookingAdmin)
        assert userfilter.lookup_choices == [
            (user.id, 'Donald Duck (dd)'),
            (self.user.id, 'Test User (testuser)')
        ]

    def test_booking_user_filter(self):
        user = baker.make_recipe(
            'booking.user', first_name='Donald', last_name='Duck',
            username='dd')
        baker.make_recipe('booking.booking', user=self.user, _quantity=5)
        baker.make_recipe('booking.booking', user=user, _quantity=5)

        userfilter = admin.UserFilter(None, {}, Booking, admin.BookingAdmin)
        result = userfilter.queryset(None, Booking.objects.all())

        # with no filter parameters, return all
        assert Booking.objects.count() == 10
        assert result.count() == 10
        assert [booking.id for booking in result] == [booking.id for booking in Booking.objects.all()]

        userfilter = admin.UserFilter(
            None, {'user': self.user.id}, Booking, admin.BookingAdmin
        )
        result = userfilter.queryset(None, Booking.objects.all())
        assert result.count() == 5
        assert [booking.id for booking in result] == [
            booking.id for booking in Booking.objects.filter(user=self.user)
        ]


class ItemVoucherAdminTests(TestCase):

    def test_get_valid_for_display(self):
        membership_type = baker.make(MembershipType, name="test membership")
        voucher = baker.make(ItemVoucher, event_types=["workshop", "private"], discount=10)
        voucher.membership_types.add(membership_type)
        voucher_admin = admin.ItemVoucherAdmin(ItemVoucher, AdminSite())
        voucher_query = voucher_admin.get_queryset(None)[0]
        assert voucher_admin.valid_for(voucher_query) == 'Membership - test membership, Workshop booking, Private Lesson booking'
    

class TotalVoucherAdminTests(TestCase):

    def test_get_queryset(self):
        voucher = baker.make(TotalVoucher, discount=10, is_gift_voucher=False)
        baker.make(TotalVoucher, discount=10, is_gift_voucher=True)
        voucher_admin = admin.TotalVoucherAdmin(TotalVoucher, AdminSite())
        assert [
            v.id for v in voucher_admin.get_queryset(None)
        ] == [voucher.id]


@pytest.mark.django_db
def test_get_gift_voucher_display(membership_gift_voucher, total_gift_voucher):
    total_gift_voucher.activate()

    gift_voucher_admin = admin.GiftVoucherAdmin(GiftVoucher, AdminSite())
    membership_gift_voucher_query = gift_voucher_admin.get_queryset(None).filter(id=membership_gift_voucher.id)[0]
    assert gift_voucher_admin.activated(membership_gift_voucher_query) is False

    total_gift_voucher_query = gift_voucher_admin.get_queryset(None).filter(id=total_gift_voucher.id)[0]
    assert gift_voucher_admin.activated(total_gift_voucher_query) is True
    
    assert gift_voucher_admin.link(total_gift_voucher_query) == (
        f'<a href="{total_gift_voucher.get_voucher_url()}">{total_gift_voucher.slug}</a>'
    )
