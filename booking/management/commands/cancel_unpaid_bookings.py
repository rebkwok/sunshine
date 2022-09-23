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
from booking.email_helpers import email_waiting_lists, send_email, send_waiting_list_email
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
