from model_bakery import baker

from django.contrib.admin.sites import AdminSite
from django.test import TestCase

from activitylog import admin
from activitylog.models import ActivityLog


class ActivityLogAdminTests(TestCase):

    def test_timestamp_display(self):
        baker.make(ActivityLog, log="New log")

        log_admin = admin.ActivityLogAdmin(ActivityLog, AdminSite())
        log_query = log_admin.get_queryset(None)[0]
        self.assertEqual(
            log_admin.timestamp_formatted(log_query),
            log_query.timestamp.strftime('%d-%b-%Y %H:%M:%S (%Z)')
        )
