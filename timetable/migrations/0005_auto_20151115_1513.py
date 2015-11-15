# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('timetable', '0004_auto_20151115_1508'),
    ]

    operations = [
        migrations.AlterField(
            model_name='timetablesession',
            name='membership_level',
            field=models.ForeignKey(null=True, verbose_name='Membership category', blank=True, to='timetable.MembershipClassLevel', help_text='Specify type of class for membership purposes'),
        ),
    ]
