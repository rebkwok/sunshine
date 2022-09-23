# -*- coding: utf-8 -*-
from calendar import monthrange, month_name
from datetime import datetime, timedelta
from decimal import Decimal
import logging
from sys import _clear_type_cache
import pytz
import shortuuid

from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.postgres.fields import ArrayField
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from django_extensions.db.fields import AutoSlugField

from activitylog.models import ActivityLog
from stripe_payments.models import Invoice
from timetable.models import Venue
from booking.utils import start_of_day_in_utc, end_of_day_in_utc, start_of_day_in_local_time

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
        valid_memberships = user.memberships.filter(
            month=self.date.month, year=self.date.year, paid=True
        ).order_by("purchase_date")
        available = next(
            (membership for membership in valid_memberships if not membership.full()),
            None
        )
        return available

    def __str__(self):
        local_datestr = self.date.astimezone(pytz.timezone('Europe/London')).strftime('%d %b %Y, %H:%M')
        return f'{self.name} - {local_datestr}'


class MembershipType(models.Model):
    name = models.CharField(max_length=255)
    number_of_classes = models.PositiveIntegerField()
    cost = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self) -> str:
        return f"{self.name} - {self.cost}"


def _start_of_today():
    now = timezone.now()
    return start_of_day_in_local_time(now)


class BaseVoucher(models.Model):
    code = models.CharField(max_length=255, unique=True)
    discount = models.PositiveIntegerField(
        verbose_name="Percentage discount", help_text="Discount value as a % of the purchased item cost. Enter a number between 1 and 100",
        null=True, blank=True
    )
    discount_amount = models.DecimalField(
        verbose_name="Exact discount amount (£)", help_text="Discount as an exact amount off the purchased item cost",
        null=True, blank=True, decimal_places=2, max_digits=6
    )
    start_date = models.DateTimeField(default=_start_of_today)
    expiry_date = models.DateTimeField(null=True, blank=True)
    max_vouchers = models.PositiveIntegerField(
        null=True, blank=True, verbose_name='Maximum available vouchers',
        help_text="Maximum uses across all users")
    max_per_user = models.PositiveIntegerField(
        null=True, blank=True,
        verbose_name="Maximum uses per user",
        help_text="Maximum times this voucher can be used by a single user"
    )

    # for gift vouchers
    is_gift_voucher = models.BooleanField(default=False)
    activated = models.BooleanField(default=True)
    name = models.CharField(null=True, blank=True, max_length=255, help_text="Name of recipient")
    message = models.TextField(null=True, blank=True, max_length=500, help_text="Message (max 500 characters)")
    purchaser_email = models.EmailField(null=True, blank=True)

    @property
    def has_expired(self):
        if self.expiry_date and self.expiry_date < timezone.now():
            return True
        return False

    @property
    def has_started(self):
        return bool(self.start_date < timezone.now() and self.activated)

    def clean(self):
        if not (self.discount or self.discount_amount):
            raise ValidationError("One of discount (%) or discount amount (fixed £ amount) is required")
        if self.discount and self.discount_amount:
            raise ValidationError("Only one of discount (%) or discount amount (fixed £ amount) may be specified (not both)")

    def _generate_code(self):
        return slugify(shortuuid.ShortUUID().random(length=12))

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = self._generate_code()
            while BaseVoucher.objects.filter(code=self.code).exists():
                self.code = self._generate_code()
        self.full_clean()
        # replace start time with very start of day
        self.start_date = start_of_day_in_utc(self.start_date)
        if self.expiry_date:
            self.expiry_date = end_of_day_in_utc(self.expiry_date)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.code


class ItemVoucher(BaseVoucher):
    membership_types = models.ManyToManyField(MembershipType, blank=True)
    event_types = ArrayField(
        models.CharField(choices=Event.EVENT_TYPES, max_length=20),
        default=list,
        null=True, blank=True
    )

    def check_membership_type(self, membership_type):
        return membership_type in self.membership_types.all()
    
    def check_event_type(self, event_type):
        return event_type in self.event_types

    def check_item(self, item):
        if isinstance(item, Membership):
            return self.check_membership_type(item.membership_type)
        else:
            assert isinstance(item, Booking)
            return self.check_event_type(item.event.event_type)

    def paid_and_unpaid_items(self, user=None):
        all_items = {
            "membership": self.memberships.all(),
            "booking": self.bookings.all()
        }
        if user is not None:
            return {
                k: v.filter(user=user) for k, v in all_items.items()
            }
        return all_items
    
    def valid_for(self):
        return list(
            f"{mem.name} (membership)" for mem in self.membership_types.all()
            ) + list(self.event_types)

    def used_items(self, user=None):
        used_items = {
            "membership": self.memberships.filter(paid=True),
            "booking": self.bookings.filter(paid=True)
        }
        if user is not None:
            return {
                k: v.filter(user=user) for k, v in used_items.items()
            }
        return used_items

    def uses(self, user=None):
        return sum([qs.count() for qs in self.used_items(user=user).values()])


class TotalVoucher(BaseVoucher):
    """A voucher that applies to the overall checkout total, not linked to any specific membership or event type"""

    def uses(self):
        return Invoice.objects.filter(paid=True, total_voucher_code=self.code).count()


class Membership(models.Model):
    user = models.ForeignKey(User, related_name="memberships", on_delete=models.CASCADE)
    membership_type = models.ForeignKey(MembershipType, related_name="memberships", on_delete=models.CASCADE)
    paid = models.BooleanField(default=False)
    purchase_date = models.DateTimeField(default=timezone.now)
    month = models.PositiveIntegerField(choices=[(i, i) for i in range(1,13)])
    year = models.PositiveIntegerField(choices=[(yr, yr) for yr in range(2022, 2035)])
    invoice = models.ForeignKey(Invoice, on_delete=models.SET_NULL, null=True, blank=True, related_name="memberships")
    voucher = models.ForeignKey(ItemVoucher, on_delete=models.SET_NULL, null=True, blank=True, related_name="memberships")

    @property
    def month_str(self):
        return month_name[self.month]

    def start_date(self): 
        return datetime(self.year, self.month, 1, tzinfo=timezone.utc)

    def expiry_date(self):
        _, last_day = monthrange(month=self.month, year=self.year)
        return datetime(self.year, self.month, last_day, tzinfo=timezone.utc)

    def has_expired(self):
        now = timezone.now()
        return now > self.expiry_date() + timedelta(days=1)

    def current_or_future(self):
        return not (self.has_expired() or self.full())

    def times_used(self):
        return self.bookings.count()

    def full(self):
        return self.times_used() >= self.membership_type.number_of_classes

    @property
    def cost_with_voucher(self):
        if not self.voucher:
            return self.membership_type.cost
        original_cost = Decimal(float(self.membership_type.cost))
        if self.voucher.discount_amount:
            if self.voucher.discount_amount > original_cost:
                return 0
            return original_cost - Decimal(self.voucher.discount_amount)
        percentage_to_pay = Decimal((100 - self.voucher.discount) / 100)
        return (original_cost * percentage_to_pay).quantize(Decimal('.01'))

    def __str__(self) -> str:
        return f"{self.membership_type.name} - {self.month_str} {self.year}"


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

    membership = models.ForeignKey(
        Membership, null=True, blank=True, 
        on_delete=models.SET_NULL,
        related_name="bookings"
    )
    invoice = models.ForeignKey(Invoice, on_delete=models.SET_NULL, null=True, blank=True, related_name="bookings")
    voucher = models.ForeignKey(ItemVoucher, on_delete=models.SET_NULL, null=True, blank=True, related_name="bookings")
    checkout_time = models.DateTimeField(null=True, blank=True)

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

    def mark_checked(self):
        self.checkout_time = timezone.now()
        self.save()

    @classmethod
    def cleanup_expired_bookings(cls, user=None, use_cache=False):
        """
        Delete bookings that are unpaid
        """
        if use_cache:
            # check cache to see if we cleaned up recently
            if cache.get("expired_bookings_cleaned"):
                logger.info("Expired bookings cleaned up within past 2 mins; no cleanup required")
                return []

        # timeout defaults to 15 mins
        timeout = settings.CART_TIMEOUT_MINUTES
        checkout_buffer_seconds = 60 * 5

        if user:
            # If we have a user, we're at the checkout, so get all unpaid bookings for
            # this user only
            unpaid_bookings = user.bookings.filter(
                event__date__gt=timezone.now(),
                status="OPEN", no_show=False,
                paid=False,
                checkout_time__lt=timezone.now() - timedelta(seconds=checkout_buffer_seconds)
            )
        else:
            # no user, doing a general cleanup.  Don't delete anything that was time-checked
            # (done at final checkout stage) within the past 5 mins, in case we delete something
            # that's in the process of being paid
            unpaid_bookings = cls.objects.filter(
                event__date__gt=timezone.now(),
                status="OPEN", no_show=False,
                paid=False, 
                checkout_time__lt=timezone.now() - timedelta(seconds=checkout_buffer_seconds)
            )
        created_dates = [
            (booking, booking.date_rebooked or booking.date_booked) 
            for booking in unpaid_bookings
        ]
        expired_ids = [
            booking.id for booking, created_at in created_dates
            if created_at < (timezone.now() - timedelta(minutes=timeout))
        ]
        expired = cls.objects.filter(id__in=expired_ids)
        event_ids = expired.values_list("event_id", flat=True)

        if expired:
            if user is not None:
                ActivityLog.objects.create(
                    log=f"{expired.count()} bookings for user {user} expired and were deleted"
                )
            else:
                ActivityLog.objects.create(
                    log=f"{expired.count()} booking cart items expired and were deleted"
                )
        expired.delete()

        if use_cache:
            logger.info("Expired bookings cleaned up")
            # cache for 2 mins
            cache.set("expired_bookings_cleaned", True, timeout=60*2)
        
        # return the event ids for bookings that were deleted, so we can check if 
        # waiting list emails need to be sent
        return event_ids

    @property
    def cost_with_voucher(self):
        if not self.voucher:
            return self.event.cost
        original_cost = Decimal(float(self.event.cost))
        if self.voucher.discount_amount:
            if self.voucher.discount_amount > original_cost:
                return 0
            return original_cost - Decimal(self.voucher.discount_amount)
        percentage_to_pay = Decimal((100 - self.voucher.discount) / 100)
        return (original_cost * percentage_to_pay).quantize(Decimal('.01'))

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
