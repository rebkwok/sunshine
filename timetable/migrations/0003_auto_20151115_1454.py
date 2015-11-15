# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('timetable', '0002_auto_20150827_2301'),
    ]

    operations = [
        migrations.AlterField(
            model_name='timetablesession',
            name='alt_cost',
            field=models.DecimalField(decimal_places=2, help_text='Cost for additional session for members', max_digits=8, blank=True, verbose_name='Member cost', null=True),
        ),
        migrations.AlterField(
            model_name='timetablesession',
            name='cost',
            field=models.DecimalField(max_digits=8, default=7, decimal_places=2, help_text='Cost for non-members'),
        ),
    ]
