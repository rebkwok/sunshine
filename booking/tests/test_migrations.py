from django.utils import timezone
from django_migration_testcase import MigrationTest


class EventCancellationFeeMigrationTests(MigrationTest):

    before = [
        ('booking', '0012_auto_20200228_1500')
    ]
    after = [
        ('booking', '0014_add_default_cancellation_fee')
    ]

    def test_data_migration_voucher_to_event_voucher(self):
        # get pre-migration models
        Event = self.get_model_before('booking.Event')

        # set up pre-migration data
        Event.objects.create(event_type='workshop', name="workshop", date=timezone.now(), cost=5)
        Event.objects.create(event_type='regular_session', name="Pole Class", date=timezone.now(), cost=10)

        # run migration
        self.run_migration()

        # get post-migration models
        Event = self.get_model_after('booking.Event')

         # check data
        for event in Event.objects.all():
            self.assertEqual(event.cancellation_fee, 1.00)