# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('timetable', '0003_auto_20150821_0832'),
    ]

    operations = [
        migrations.AddField(
            model_name='instructor',
            name='index',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]
