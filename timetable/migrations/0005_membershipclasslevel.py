# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('timetable', '0004_auto_20150815_1050'),
    ]

    operations = [
        migrations.CreateModel(
            name='MembershipClassLevel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', auto_created=True, serialize=False, primary_key=True)),
                ('membership_level', models.PositiveIntegerField()),
            ],
        ),
    ]
