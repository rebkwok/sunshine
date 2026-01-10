from datetime import timedelta

from model_bakery import baker

from django.core import management, mail
from django.test import TestCase, override_settings
from django.utils import timezone

from accounts.models import ArchivedDisclaimer, OnlineDisclaimer
from activitylog.models import ActivityLog

from conftest import make_online_disclaimer, make_archived_disclaimer


class DeleteExpiredDisclaimersTests(TestCase):

    def setUp(self):
        super(DeleteExpiredDisclaimersTests, self).setUp()
        self.user = baker.make_recipe(
            'booking.user', first_name='Test', last_name='User')
        make_online_disclaimer(user=self.user,
            date=timezone.now()-timedelta(2200)  # > 6 yrs
        )
        self.user1 = baker.make_recipe(
            'booking.user', first_name='Test', last_name='User2'
        )
        make_online_disclaimer(
            user=self.user1,
            date=timezone.now()-timedelta(2200)  # > 6 yrs
        )

        make_archived_disclaimer(name='Test Archived',
            date=timezone.now()-timedelta(2200)  # > 6 yrs
        )

    def test_disclaimers_deleted_if_more_than_6_years_old(self):
        self.assertEqual(OnlineDisclaimer.objects.count(), 2)

        management.call_command('delete_expired_disclaimers')
        self.assertEqual(OnlineDisclaimer.objects.count(), 0)

        activitylogs = ActivityLog.objects.values_list('log', flat=True)

        online_users = [
            '{} {}'.format(user.first_name, user.last_name)
            for user in [self.user, self.user1]
        ]

        self.assertIn(
            'Online disclaimers more than 6 yrs old deleted for users: {}'.format(
                ', '.join(online_users)
            ),
            activitylogs
        )

        self.assertIn(
            'Archived disclaimers more than 6 yrs old deleted for users: Test Archived',
            activitylogs
        )

    def test_disclaimers_not_deleted_if_created_in_past_6_years(self):
        # make a user with a disclaimer created today
        user = baker.make_recipe('booking.user')
        make_online_disclaimer(user=user)
        make_archived_disclaimer()

        self.assertEqual(OnlineDisclaimer.objects.count(), 3)
        self.assertEqual(ArchivedDisclaimer.objects.count(), 2)

        # disclaimer should not be deleted because it was created < 3 yrs ago.
        # All others will be.
        management.call_command('delete_expired_disclaimers')
        self.assertEqual(OnlineDisclaimer.objects.count(), 1)

    def test_disclaimers_not_deleted_if_updated_in_past_6_years(self):
        # make a user with a disclaimer created > yr ago but updated in past yr
        user = baker.make_recipe('booking.user')
        make_online_disclaimer(user=user, date=timezone.now() - timedelta(2200),
            date_updated=timezone.now() - timedelta(2000),
        )
        self.assertEqual(OnlineDisclaimer.objects.count(), 3)

        management.call_command('delete_expired_disclaimers')
        self.assertEqual(OnlineDisclaimer.objects.count(), 1)

    def test_no_disclaimers_to_delete(self):
        for disclaimer_list in [
            OnlineDisclaimer.objects.all(), ArchivedDisclaimer.objects.all()
        ]:
            for disclaimer in disclaimer_list:
                if hasattr(disclaimer, 'date_updated'):
                    disclaimer.date_updated = timezone.now() - timedelta(600)
                    disclaimer.save()
                else:
                    disclaimer.delete()

        management.call_command('delete_expired_disclaimers')
        self.assertEqual(OnlineDisclaimer.objects.count(), 2)
        self.assertEqual(ArchivedDisclaimer.objects.count(), 1)
