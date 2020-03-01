
from django.db import migrations


def default_cancellation_fees(apps, schema_editor):
    TimetableSession = apps.get_model('timetable', 'TimetableSession')
    for timetable_session in TimetableSession.objects.all():
        timetable_session.cancellation_fee = 1.0
        timetable_session.save()


class Migration(migrations.Migration):

    dependencies = [
        ('timetable', '0013_timetablesession_cancellation_fee'),
    ]

    operations = [
        migrations.RunPython(default_cancellation_fees),
    ]
