# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('timetable', '0002_sessiontype_index'),
    ]

    operations = [
        migrations.CreateModel(
            name='TimetableSession',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, auto_created=True, verbose_name='ID')),
                ('level', models.CharField(default='All levels', max_length=255)),
                ('session_day', models.CharField(default='01MO', choices=[('01MO', 'Monday'), ('02TU', 'Tuesday'), ('03WE', 'Wednesday'), ('04TH', 'Thursday'), ('05FR', 'Friday'), ('06SA', 'Saturday'), ('07SU', 'Sunday')], max_length=4)),
                ('session_time', models.TimeField()),
                ('duration', models.IntegerField(default=60, verbose_name='duration (mins)')),
                ('instructor', models.ForeignKey(null=True, blank=True, to='timetable.Instructor')),
                ('session_type', models.ForeignKey(to='timetable.SessionType')),
                ('venue', models.ForeignKey(to='timetable.Venue')),
            ],
        ),
        migrations.RemoveField(
            model_name='event',
            name='venue',
        ),
        migrations.RemoveField(
            model_name='fixedsession',
            name='instructor',
        ),
        migrations.RemoveField(
            model_name='fixedsession',
            name='session_type',
        ),
        migrations.RemoveField(
            model_name='fixedsession',
            name='venue',
        ),
        migrations.RemoveField(
            model_name='session',
            name='instructor',
        ),
        migrations.RemoveField(
            model_name='session',
            name='session_type',
        ),
        migrations.RemoveField(
            model_name='session',
            name='venue',
        ),
        migrations.DeleteModel(
            name='Event',
        ),
        migrations.DeleteModel(
            name='FixedSession',
        ),
        migrations.DeleteModel(
            name='Session',
        ),
    ]
