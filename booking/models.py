# -*- coding: utf-8 -*-

import logging
import pytz
import shortuuid

from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _

from django_extensions.db.fields import AutoSlugField

from timetable.models import Venue

logger = logging.getLogger(__name__)


class Event(models.Model):
    EVENT_TYPES = (('workshop', 'Workshop'), ('regular_session', 'Regular Timetabled Session'))

    name = models.CharField(max_length=255)
    event_type = models.CharField(
        choices=EVENT_TYPES, default='workshop', max_length=255
    )
    description = models.TextField(blank=True, default="")
    date = models.DateTimeField()
    venue = models.ForeignKey(Venue, null=True, on_delete=models.SET_NULL)
    max_participants = models.PositiveIntegerField(default=12)

    contact_email = models.EmailField(default="carouselfitness@gmail.com")
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
    email_studio_when_booked = models.BooleanField(default=True)
    slug = AutoSlugField(
        populate_from=['name', 'date'], max_length=40, unique=True
    )
    allow_booking_cancellation = models.BooleanField(default=True)
    paypal_email = models.EmailField(
        default=settings.DEFAULT_PAYPAL_EMAIL,
        help_text='Email for the paypal account to be used for payment.  '
                  'Check this carefully!'
    )
    cancelled = models.BooleanField(default=False)

    class Meta:
        ordering = ['-date']
        verbose_name = 'Workshop/Class'
        verbose_name_plural = 'Workshops/Classes'

    @cached_property
    def spaces_left(self):
        booked_number = Booking.objects.select_related('event', 'user').filter(
            event__id=self.id, status='OPEN', no_show=False
        ).count()
        return self.max_participants - booked_number

    @cached_property
    def bookable(self):
        return self.spaces_left > 0

    def can_cancel(self):
        time_until_event = self.date - timezone.now()
        time_until_event = time_until_event.total_seconds() / 3600
        return (
            self.allow_booking_cancellation and
            time_until_event > self.cancellation_period
        )

    def get_absolute_url(self):
        return reverse("booking:event_detail", kwargs={'slug': self.slug})

    def __str__(self):
        return '{} - {}'.format(
            str(self.name),
            self.date.astimezone(
                pytz.timezone('Europe/London')
            ).strftime('%d %b %Y, %H:%M')
        )


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

    class Meta:
        unique_together = ('user', 'event')

    def __str__(self):
        return "{} - {}".format(str(self.event.name), str(self.user.username))

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

    def save(self, *args, **kwargs):

        rebooking = self._is_rebooking()
        new_booking = self._is_new_booking()

        if new_booking:
            self.booking_reference = shortuuid.ShortUUID().random(length=22)

        self.full_clean()

        if rebooking:
            self.date_rebooked = timezone.now()

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
