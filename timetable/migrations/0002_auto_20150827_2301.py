# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('timetable', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='MembershipClassLevel',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, verbose_name='ID', auto_created=True)),
                ('membership_level', models.PositiveIntegerField()),
            ],
        ),
        migrations.CreateModel(
            name='TimetableSession',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, verbose_name='ID', auto_created=True)),
                ('level', models.CharField(max_length=255, default='All levels')),
                ('session_day', models.CharField(max_length=4, choices=[('01MO', 'Monday'), ('02TU', 'Tuesday'), ('03WE', 'Wednesday'), ('04TH', 'Thursday'), ('05FR', 'Friday'), ('06SA', 'Saturday'), ('07SU', 'Sunday')])),
                ('start_time', models.TimeField()),
                ('end_time', models.TimeField()),
                ('name', models.CharField(max_length=255, default='')),
                ('cost', models.DecimalField(decimal_places=2, null=True, max_digits=8)),
                ('alt_cost', models.DecimalField(decimal_places=2, null=True, max_digits=8)),
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
        migrations.AddField(
            model_name='instructor',
            name='index',
            field=models.PositiveIntegerField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='sessiontype',
            name='index',
            field=models.PositiveIntegerField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='venue',
            name='abbreviation',
            field=models.CharField(max_length=20, default=''),
        ),
        migrations.AlterField(
            model_name='instructor',
            name='info',
            field=models.TextField(verbose_name='instructor description', null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='instructor',
            name='photo',
            field=models.ImageField(upload_to='instructors', null=True, help_text='Please upload a .jpg image with equal height and width', blank=True),
        ),
        migrations.AlterField(
            model_name='instructor',
            name='regular_instructor',
            field=models.BooleanField(help_text='Tick this box to list this instructor on the Instructors webpage', default=True),
        ),
        migrations.AlterField(
            model_name='sessiontype',
            name='info',
            field=models.TextField(verbose_name='session description', null=True),
        ),
        migrations.AlterField(
            model_name='sessiontype',
            name='photo',
            field=models.ImageField(upload_to='sessions', null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='sessiontype',
            name='regular_session',
            field=models.BooleanField(verbose_name='display session', help_text='Tick this box to list this class type on the homepage and class description pages', default=True),
        ),
        migrations.AlterField(
            model_name='venue',
            name='venue',
            field=models.CharField(max_length=255, default='Venue TBC'),
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
        migrations.AddField(
            model_name='timetablesession',
            name='instructor',
            field=models.ForeignKey(to='timetable.Instructor', null=True, blank=True, on_delete=models.SET_NULL),
        ),
        migrations.AddField(
            model_name='timetablesession',
            name='membership_level',
            field=models.ForeignKey(to='timetable.MembershipClassLevel', null=True, help_text='Categorise for membership; 1=pole/hoop classes, 2=general fitness/conditioning classes', on_delete=models.SET_NULL),
        ),
        migrations.AddField(
            model_name='timetablesession',
            name='session_type',
            field=models.ForeignKey(to='timetable.SessionType', on_delete=models.CASCADE),
        ),
        migrations.AddField(
            model_name='timetablesession',
            name='venue',
            field=models.ForeignKey(to='timetable.Venue', on_delete=models.CASCADE),
        ),
    ]
