# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('timetable', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='timetablesession',
            name='alt_cost',
            field=models.DecimalField(default=5, decimal_places=2, null=True, max_digits=8),
        ),
        migrations.AddField(
            model_name='timetablesession',
            name='cost',
            field=models.DecimalField(default=7, decimal_places=2, null=True, max_digits=8),
        ),
    ]
