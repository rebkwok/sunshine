# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Event',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255)),
                ('event_date', models.DateTimeField(verbose_name=b'event date')),
                ('end_time', models.TimeField(null=True, verbose_name=b'end time', blank=True)),
                ('info', models.TextField(null=True, verbose_name=b'event description', blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='FixedSession',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('level', models.CharField(default=b'All levels', max_length=255)),
                ('session_day', models.CharField(default=b'01MO', max_length=4, choices=[(b'01MO', b'Monday'), (b'02TU', b'Tuesday'), (b'03WE', b'Wednesday'), (b'04TH', b'Thursday'), (b'05FR', b'Friday'), (b'06SA', b'Saturday'), (b'07SU', b'Sunday')])),
                ('session_time', models.TimeField()),
                ('duration', models.IntegerField(default=60, verbose_name=b'duration (mins)')),
                ('spaces', models.BooleanField(default=True, verbose_name=b'spaces available')),
                ('show_instructor', models.BooleanField(default=False, help_text=b'Tick this box to show a link to the instructor on the timetable pages (mostly for workshops and one-off classes where the instructor is not a regular instructor and will not appear on the instructor pages by default)', verbose_name=b'show instructor')),
            ],
        ),
        migrations.CreateModel(
            name='Instructor',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255)),
                ('info', models.TextField(null=True, verbose_name=b'instructor description', blank=True)),
                ('regular_instructor', models.BooleanField(default=True, help_text=b'Tick this box to list this instructor on the Instructors webpage')),
                ('photo', models.ImageField(help_text=b'Please upload a .jpg image with equal height and width', null=True, upload_to=b'instructors', blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='Session',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('level', models.CharField(default=b'All levels', max_length=255)),
                ('session_date', models.DateTimeField(verbose_name=b'session date')),
                ('duration', models.IntegerField(default=60, verbose_name=b'duration (mins)')),
                ('spaces', models.BooleanField(default=True, verbose_name=b'spaces available')),
                ('show_instructor', models.BooleanField(default=False, help_text=b'Tick this box to show a link to the instructor on the timetable pages (mostly for workshops and one-off classes where the instructor is not a regular instructor and will not appear on the instructor pages by default)', verbose_name=b'show instructor')),
                ('instructor', models.ForeignKey(blank=True, to='timetable.Instructor', null=True)),
            ],
        ),
        migrations.CreateModel(
            name='SessionType',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255)),
                ('info', models.TextField(null=True, verbose_name=b'session description')),
                ('regular_session', models.BooleanField(default=True, help_text=b'Tick this box to list this class type on the homepage and class description pages', verbose_name=b'display session')),
                ('photo', models.ImageField(null=True, upload_to=b'sessions', blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='Venue',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('venue', models.CharField(default=b'Venue TBC', max_length=255)),
                ('address', models.CharField(max_length=255, null=True, blank=True)),
                ('postcode', models.CharField(max_length=255, null=True, blank=True)),
            ],
        ),
        migrations.AddField(
            model_name='session',
            name='session_type',
            field=models.ForeignKey(to='timetable.SessionType'),
        ),
        migrations.AddField(
            model_name='session',
            name='venue',
            field=models.ForeignKey(to='timetable.Venue'),
        ),
        migrations.AddField(
            model_name='fixedsession',
            name='instructor',
            field=models.ForeignKey(blank=True, to='timetable.Instructor', null=True),
        ),
        migrations.AddField(
            model_name='fixedsession',
            name='session_type',
            field=models.ForeignKey(to='timetable.SessionType'),
        ),
        migrations.AddField(
            model_name='fixedsession',
            name='venue',
            field=models.ForeignKey(to='timetable.Venue'),
        ),
        migrations.AddField(
            model_name='event',
            name='venue',
            field=models.ForeignKey(blank=True, to='timetable.Venue', null=True),
        ),
    ]
