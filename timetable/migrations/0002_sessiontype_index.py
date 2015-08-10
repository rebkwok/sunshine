# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('timetable', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='sessiontype',
            name='index',
            field=models.PositiveIntegerField(null=True, blank=True),
        ),
    ]
