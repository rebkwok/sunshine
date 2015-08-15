# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('timetable', '0003_auto_20150815_0941'),
    ]

    operations = [
        migrations.AddField(
            model_name='timetablesession',
            name='name',
            field=models.CharField(default='', max_length=255),
        ),
        migrations.AlterField(
            model_name='timetablesession',
            name='session_day',
            field=models.CharField(choices=[('01MO', 'Monday'), ('02TU', 'Tuesday'), ('03WE', 'Wednesday'), ('04TH', 'Thursday'), ('05FR', 'Friday'), ('06SA', 'Saturday'), ('07SU', 'Sunday')], max_length=4),
        ),
    ]
