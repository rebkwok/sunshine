# -*- coding: utf-8 -*-

import logging
import pytz

from datetime import timedelta, datetime
from booking.models import Event
from .models import TimetableSession
from activitylog.models import ActivityLog


logger = logging.getLogger(__name__)


def upload_timetable(start_date, end_date, session_ids, show_on_site, user=None):

    daylist = [
        '01MO',
        '02TU',
        '03WE',
        '04TH',
        '05FR',
        '06SA',
        '07SU'
        ]

    created_classes = []
    existing_classes = []
    duplicate_classes = []

    d = start_date
    delta = timedelta(days=1)
    while d <= end_date:
        sessions_to_create = TimetableSession.objects.filter(
            session_day=daylist[d.weekday()], id__in=session_ids
        )
        for session in sessions_to_create:

            # create date in Europe/London, convert to UTC
            localtz = pytz.timezone('Europe/London')
            local_date = localtz.localize(datetime.combine(d,
                session.start_time))
            converted_date = local_date.astimezone(pytz.utc)
            name = '{} ({})'.format(session.name, session.level)
            
            event_type = "private" if session.session_type.name.lower().strip().startswith("private") else "regular_session"

            existing = Event.objects.filter(
                name=name,
                event_type=event_type,
                date=converted_date,
                venue=session.venue,
            )
            if not existing:
                cl = Event.objects.create(
                    name=name,
                    event_type=event_type,
                    date=converted_date,
                    venue=session.venue,
                    max_participants=session.max_participants,
                    cost=session.cost,
                    show_on_site=show_on_site,
                    cancellation_period=session.cancellation_period,
                    cancellation_fee=session.cancellation_fee,
                    members_only=session.members_only,
                )
                created_classes.append(cl)
            else:
                if existing.count() > 1:
                    duplicate_classes.append(
                        {'class': existing[0], 'count': existing.count()}
                    )
                existing_classes.append(existing[0])
        d += delta

    if created_classes:
        ActivityLog.objects.create(
            log='Timetable uploaded for {} to {} {}'.format(
                start_date.strftime('%a %d %B %Y'),
                end_date.strftime('%a %d %B %Y'),
                'by admin user {}'.format(user.username) if user else ''
            )
        )

    return created_classes, existing_classes, duplicate_classes
