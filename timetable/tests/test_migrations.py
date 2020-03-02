from datetime import time
from django_migration_testcase import MigrationTest


class EventCancellationFeeMigrationTests(MigrationTest):

    before = [
        ('timetable', '0012_auto_20191020_1524')
    ]
    after = [
        ('timetable', '0014_add_default_cancellation_fee')
    ]

    def test_data_migration_voucher_to_event_voucher(self):
        # get pre-migration models
        TimetableSession = self.get_model_before('timetable.TimetableSession')
        SessionType = self.get_model_before('timetable.SessionType')
        Venue = self.get_model_before('timetable.Venue')

        session_type = SessionType.objects.create(name="test")
        venue = Venue.objects.create(venue="test")
        # set up pre-migration data
        TimetableSession.objects.create(
            name="Pole Class 1", cost=5, session_day='01MO', start_time=time(12, 0), end_time=time(13, 0),
            session_type=session_type, venue=venue
        )
        TimetableSession.objects.create(
            name="Pole Class 2", cost=10, session_day='02TU',  start_time=time(18, 0), end_time=time(19, 0),
            session_type=session_type, venue=venue
        )

        # run migration
        self.run_migration()

        # get post-migration models
        TimetableSession = self.get_model_after('timetable.TimetableSession')

         # check data
        for timetablesession in TimetableSession.objects.all():
            self.assertEqual(timetablesession.cancellation_fee, 1.00)
