"""
Email reminders for upcoming events
Check for events with date within 48 hrs, but not ones booked/rebooked within the last 6 hrs
Assume that if you just booked, you don't need a reminder immediately
Email all users on event.bookings where booking.status == 'OPEN' and paid=True
Add reminder_sent flag to booking model so we don't keep sending
"""

from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Q
from booking.email_helpers import send_email
from booking.models import Booking, Event
from activitylog.models import ActivityLog


class Command(BaseCommand):
    help = "email reminders for upcoming (paid) bookings"

    def handle(self, *args, **options):
        target_time = timezone.now() + timedelta(hours=48)
        events = Event.objects.filter(
            Q(cancelled=False) & Q(date__gte=timezone.now()) & Q(date__lte=target_time)
        )

        upcoming_bookings = Booking.objects.filter(
            event__in=events,
            status="OPEN",
            no_show=False,
            reminder_sent=False,
            paid=True,
            date_booked__lt=timezone.now() - timedelta(hours=6),
        )

        reminded_bookings = []
        for booking in upcoming_bookings:
            if booking.date_rebooked and booking.date_rebooked > (
                timezone.now() - timedelta(hours=6)
            ):
                continue
            reminded_bookings.append(booking.id)
            ctx = {
                "booking": booking,
                "event": booking.event,
                "date": booking.event.date.strftime("%A %d %B"),
                "time": booking.event.date.strftime("%I:%M %p"),
                "ev_type": "workshop"
                if booking.event.event_type == "workshop"
                else "class",
                "domain": settings.DOMAIN,
            }
            send_email(
                None,
                f"Reminder: your booking for {booking.event}",
                ctx,
                template_txt="booking/email/booking_reminder.txt",
                template_html="booking/email/booking_reminder.html",
                prefix=settings.ACCOUNT_EMAIL_SUBJECT_PREFIX,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to_list=[booking.user.email],
            )
            booking.reminder_sent = True
            booking.save()

            ActivityLog.objects.create(
                log="Reminder email sent for booking id {} for event {}, "
                "user {}".format(booking.id, booking.event, booking.user.username)
            )

        if upcoming_bookings:
            self.stdout.write(
                "Reminder emails sent for booking ids {}".format(
                    ", ".join([str(id) for id in reminded_bookings])
                )
            )

        else:
            self.stdout.write("No reminders to send")
