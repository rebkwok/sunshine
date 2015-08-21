# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('timetable', '0002_auto_20150821_0824'),
    ]

    operations = [
        migrations.AlterField(
            model_name='timetablesession',
            name='alt_cost',
            field=models.DecimalField(decimal_places=2, null=True, max_digits=8),
        ),
        migrations.AlterField(
            model_name='timetablesession',
            name='cost',
            field=models.DecimalField(decimal_places=2, null=True, max_digits=8),
        ),
    ]
