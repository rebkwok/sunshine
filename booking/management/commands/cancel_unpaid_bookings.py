# -*- coding: utf-8 -*-

"""
Check for unpaid bookings and cancel where:
booking.status = OPEN
paid = False
Booking date booked OR booking date rebooked > 6 hrs ago)
Email user that their booking has been cancelled
"""

import logging
from datetime import timedelta

from django.utils import timezone
from django.core.management.base import BaseCommand

from booking.models import Booking, WaitingListUser
from booking.email_helpers import send_email, send_waiting_list_email
from activitylog.models import ActivityLog


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Cancel unpaid bookings 6 hrs after booked/rebooked'

    def handle(self, *args, **options):

        bookings = []
        for booking in Booking.objects.filter(
            event__date__gte=timezone.now(),
            status='OPEN',
            paid=False,
            date_booked__lte=timezone.now() - timedelta(hours=24)
        ):
            # ignore any which have been rebooked in the past 24 hrs
            if not (
                        booking.date_rebooked and
                    (
                                booking.date_rebooked >= timezone.now() -
                                timedelta(hours=24)
                    )
            ):
               bookings.append(booking)

        for booking in bookings:
            event_was_full = booking.event.spaces_left == 0

            ctx = {
                  'booking': booking,
                  'event': booking.event,
                  'date': booking.event.date.strftime('%A %d %B'),
                  'time': booking.event.date.strftime('%I:%M %p'),
            }

            # send mails to user
            send_email(
                None, 'Booking cancelled: {}'.format(booking.event.name), ctx,
                'booking/email/booking_auto_cancelled.txt',
                'booking/email/booking_auto_cancelled.html',
                to_list=[booking.user.email]
            )

            booking.status = 'CANCELLED'
            booking.save()
            ActivityLog.objects.create(
                log='Unpaid booking id {} for workshop {}, user {} '
                    'automatically cancelled'.format(
                        booking.id, booking.event, booking.user
                )
            )
            if event_was_full:
                waiting_list_users = WaitingListUser.objects.filter(
                    event=booking.event
                )
                send_waiting_list_email(
                    booking.event,  [user.user for user in waiting_list_users]
                )
                ActivityLog.objects.create(
                    log='Waiting list email sent to user(s) {} for '
                    'event {}'.format(
                        ', '.join(
                            [
                                wluser.user.username for
                                wluser in waiting_list_users
                                ]
                        ),
                        booking.event
                    )
                )
