# -*- coding: utf-8 -*-
from calendar import monthrange
from datetime import datetime, timedelta
import logging
import pytz
import shortuuid

from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from django_extensions.db.fields import AutoSlugField

from activitylog.models import ActivityLog
from stripe_payments.models import Invoice
from timetable.models import Venue

logger = logging.getLogger(__name__)


class Event(models.Model):
    EVENT_TYPES = (('workshop', 'Workshop'), ('regular_session', 'Regular Timetabled Session'), ('private', "Private Lesson"))

    name = models.CharField(max_length=255)
    event_type = models.CharField(
        choices=EVENT_TYPES, default='regular_session', max_length=255
    )
    description = models.TextField(blank=True, default="")
    date = models.DateTimeField()
    venue = models.ForeignKey(Venue, null=True, on_delete=models.SET_NULL)
    max_participants = models.PositiveIntegerField(default=12)

    contact_email = models.EmailField(default="sunshinefitnessfife@gmail.com")
    cost = models.DecimalField(max_digits=8, decimal_places=2)

    show_on_site = models.BooleanField(
        default=False,
        help_text="Display this event/workshop on the website "
                  "(if unticked, it will still be displayed for staff users "
                  "for preview)"
    )

    cancellation_period = models.PositiveIntegerField(
        default=24
    )
    email_studio_when_booked = models.BooleanField(default=False)
    slug = AutoSlugField(
        populate_from=['name', 'date'], max_length=40, unique=True
    )
    allow_booking_cancellation = models.BooleanField(default=True)
    cancelled = models.BooleanField(default=False)
    cancellation_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    members_only = models.BooleanField(default=False, help_text="Classes are only available to students with memberships")

    class Meta:
        ordering = ['-date']
        verbose_name = 'Workshop/Class'
        verbose_name_plural = 'Workshops/Classes'
        indexes = [
            models.Index(fields=['date', 'event_type']),
        ]

    @property
    def spaces_left(self):
        booked_number = Booking.objects.select_related('event', 'user').filter(
            event__id=self.id, status='OPEN', no_show=False
        ).count()
        return self.max_participants - booked_number

    @property
    def bookable(self):
        return self.spaces_left > 0 and not self.cancelled

    def can_cancel(self):
        time_until_event = self.date - timezone.now()
        time_until_event = time_until_event.total_seconds() / 3600
        return (
            self.allow_booking_cancellation and
            time_until_event > self.cancellation_period
        )

    def get_available_user_membership(self, user):
        if self.event_type != "regular_session":
            # memberships are only valid for regular classes
            return None 
        return None

    def __str__(self):
        return '{} - {}'.format(
            str(self.name),
            self.date.astimezone(
                pytz.timezone('Europe/London')
            ).strftime('%d %b %Y, %H:%M')
        )


class MembershipType(models.Model):
    name = models.CharField(max_length=255)
    number_of_classes = models.PositiveIntegerField()
    cost = models.PositiveIntegerField(default=12)


class Membership(models.Model):
    user = models.ForeignKey(User, related_name="memberships", on_delete=models.CASCADE)
    membership_type = models.ForeignKey(MembershipType, related_name="memberships", on_delete=models.CASCADE)
    paid = models.BooleanField(default=False)
    purchase_date = models.DateTimeField(default=timezone.now)
    month = models.PositiveIntegerField(choices=[(i, i) for i in range(1,13)])
    year = models.PositiveIntegerField(choices=[(yr, yr) for yr in range(2022, 2035)])
    invoice = models.ForeignKey(Invoice, on_delete=models.SET_NULL, null=True, blank=True, related_name="user_memberships")

    def start_date(self): 
        return datetime(self.year, self.month, 1)

    def expiry_date(self):
        _, last_day = monthrange(month=self.month, year=self.year)
        return datetime(self.year, self.month, last_day)

    def is_current(self):
        now = timezone.now()
        return now.year == self.year and now.month == self.month

    def has_expired(self):
        now = timezone.now()
        return now > self.expiry_date() + timedelta(days=1)

    def full(self):
        return self.bookings.count() >= self.membership.number_of_classes


class Booking(models.Model):
    STATUS_CHOICES = (
        ('OPEN', 'Open'),
        ('CANCELLED', 'Cancelled')
    )

    booking_reference = models.CharField(max_length=22)
    user = models.ForeignKey(
        User, related_name='bookings', on_delete=models.CASCADE
    )
    event = models.ForeignKey(
        Event, related_name='bookings', on_delete=models.CASCADE
    )
    paid = models.BooleanField(
        default=False,
        help_text='Payment has been made by user'
    )

    date_booked = models.DateTimeField(default=timezone.now)
    date_rebooked = models.DateTimeField(null=True, blank=True)

    status = models.CharField(
        max_length=255, choices=STATUS_CHOICES, default='OPEN'
    )
    attended = models.BooleanField(
        default=False, help_text='Attended this event')
    no_show = models.BooleanField(
        default=False, help_text='Booked but did not attend OR cancelled '
                                 'after allowed cancellation period'
    )
    reminder_sent = models.BooleanField(default=False)

    cancellation_fee_incurred = models.BooleanField(default=False)
    cancellation_fee_paid = models.BooleanField(default=False)
    date_cancelled = models.DateTimeField(null=True, blank=True)

    stripe_pending = models.BooleanField(default=False)
    membership = models.ForeignKey(
        Membership, null=True, blank=True, 
        on_delete=models.SET_NULL,
        related_name="bookings"
    )
    invoice = models.ForeignKey(Invoice, on_delete=models.SET_NULL, null=True, blank=True, related_name="bookings")

    class Meta:
        unique_together = ('user', 'event')

    def __str__(self):
        return "{} - {}".format(str(self.event.name), str(self.user.username))

    def booked_with_membership_within_allowed_time(self):
        allowed_datetime = timezone.now() - timedelta(minutes=5)
        if self.membership:
            return (self.date_rebooked and self.date_rebooked > allowed_datetime) \
                   or (self.date_booked > allowed_datetime)
        return False

    @classmethod
    def cleanup_expired_purchases(cls, user):
        bookings = user.bookings.filter(
            event__date__gt=timezone.now(),
            status="OPEN", no_show=False,
            paid=False, stripe_pending=False
        )
        created_dates = [
            (booking, booking.date_rebooked or booking.date_booked) 
            for booking in bookings
        ]
        for booking, created_at in created_dates:
            if created_at < (timezone.now() - timedelta(settings.CART_TIMEOUT_MINUTES)):
                booking.delete()

    def _old_booking(self):
        if self.pk:
            return Booking.objects.get(pk=self.pk)

    def _is_new_booking(self):
        if not self.pk:
            return True

    def _is_rebooking(self):
        if not self.pk:
            return False
        was_cancelled = self._old_booking().status == 'CANCELLED' \
            and self.status == 'OPEN'
        was_no_show = self._old_booking().no_show and not self.no_show
        return was_cancelled or was_no_show

    def _is_cancelling(self):
        if not self.pk:
            return False
        cancelling = self._old_booking().status == 'OPEN' and self.status == 'CANCELLED'
        setting_as_no_show = self.no_show and not self._old_booking().no_show
        return cancelling or setting_as_no_show

    def clean(self):
        if self._is_rebooking():
            if self.event.spaces_left == 0:
                raise ValidationError(
                    _('Attempting to reopen booking for full '
                      'event %s' % self.event.id)
                )

        if self._is_new_booking() and self.status != "CANCELLED" and \
                self.event.spaces_left == 0:
                    raise ValidationError(
                        _('Attempting to create booking for full '
                          'event %s' % self.event.id)
                    )

        if self.attended and self.no_show:
            raise ValidationError(
                _('Cannot mark booking as both attended and no-show')
            )

    def save(self, *args, **kwargs):

        rebooking = self._is_rebooking()
        new_booking = self._is_new_booking()
        cancellation = self._is_cancelling()

        if new_booking:
            self.booking_reference = shortuuid.ShortUUID().random(length=22)

        self.full_clean()

        if rebooking:
            self.date_rebooked = timezone.now()
            self.date_cancelled = None
            if self.cancellation_fee_incurred:
                self.cancellation_fee_incurred = False
                self.cancellation_fee_paid = False
                ActivityLog.objects.create(
                    log=f"Booking {self.id} re-booked; cancellation fee rescinded."
                )
        if cancellation:
            self.date_cancelled = timezone.now()
            if not self.event.cancelled and self.event.cancellation_fee > 0 and not self.event.can_cancel():
                self.cancellation_fee_incurred = True
                ActivityLog.objects.create(
                    log=f"Booking {self.id} cancelled after cancellation period; cancellation fee cancellation_fee_incurred."
                )
        # we shouldn't ever set cancellation fee paid without it also being flagged as incurred
        if self.cancellation_fee_paid:
            self.cancellation_fee_incurred = True
        super(Booking, self).save(*args, **kwargs)


class WaitingListUser(models.Model):
    """
    A model to represent a single user on a waiting list for an event
    """
    user = models.ForeignKey(
        User, related_name='waitinglists', on_delete=models.CASCADE
    )
    event = models.ForeignKey(
        Event, related_name='waitinglistusers', on_delete=models.CASCADE
    )
    # date user joined the waiting list
    date_joined = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = 'waiting list'
        verbose_name_plural = 'waiting list'


class WorkshopManager(models.Manager):

    def get_queryset(self):
        return super().get_queryset().filter(event_type='workshop')


class RegularSessionManager(models.Manager):

    def get_queryset(self):
        return super().get_queryset().filter(event_type='regular_session')


class PrivateManager(models.Manager):

    def get_queryset(self):
        return super().get_queryset().filter(event_type='private')


class Workshop(Event):
    objects = WorkshopManager()

    class Meta:
        proxy = True


class RegularClass(Event):

    objects = RegularSessionManager()

    class Meta:
        proxy = True
        verbose_name_plural = 'regular classes'


class Private(Event):

    objects = PrivateManager()

    class Meta:
        proxy = True
        verbose_name = 'private lesson'
        verbose_name_plural = 'private lessons'


def user_str_patch(self):
    return '%s %s (%s)' % (self.first_name, self.last_name, self.username)


def has_outstanding_fees(self):
    return any(
        booking.cancellation_fee_incurred
        and not booking.cancellation_fee_paid
        and booking.event.cancellation_fee > 0
        for booking in self.bookings.all()
    )


def outstanding_fees_total(self):
    bookings_with_fees = self.bookings.filter(cancellation_fee_incurred=True, cancellation_fee_paid=False)
    return sum(booking.event.cancellation_fee for booking in bookings_with_fees)

User.add_to_class("has_outstanding_fees", has_outstanding_fees)
User.add_to_class("outstanding_fees_total", outstanding_fees_total)
User.__str__ = user_str_patch
