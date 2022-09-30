# -*- coding: utf-8 -*-

"""
Check for unpaid bookings and delete where:
booking.status = OPEN
no_show = False
paid = False

date_booked OR date_rebooked (whichever is later) is > settings.CART_TIMEOUT_MINUTES
ago (15 mins by default)
BUT excluding bookings with a checkout_time in the past 5 mins
(checkout_time is set when user clicks button to pay with stripe)

If any bookings for events are cancelled, and the event has a waiting list, send emails
"""

import logging
from django.core.management.base import BaseCommand

from booking.models import Booking
from booking.email_helpers import email_waiting_lists
from activitylog.models import ActivityLog


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Cleanup unpaid bookings that have expired'

    def handle(self, *args, **options):
        # delete old nothing-to-cancel logs
        cron_log_msg = 'CRON: booking cleanup run; nothing to delete'
        ActivityLog.objects.filter(log=cron_log_msg).delete()
        event_ids_from_expired_bookings = Booking.cleanup_expired_bookings()
        email_waiting_lists(event_ids_from_expired_bookings)
        
        if not event_ids_from_expired_bookings:
            ActivityLog.objects.create(log=cron_log_msg)
