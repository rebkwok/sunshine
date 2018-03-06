# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('timetable', '0003_auto_20151115_1454'),
    ]

    operations = [
        migrations.AlterField(
            model_name='membershipclasslevel',
            name='membership_level',
            field=models.PositiveIntegerField(help_text='Index of class type for membership; 1=pole/hoop, 2=general fitness, 3=open training'),
        ),
        migrations.AlterField(
            model_name='timetablesession',
            name='membership_level',
            field=models.ForeignKey(null=True, verbose_name='Membership category', help_text='Specify type of class for membership purposes', to='timetable.MembershipClassLevel', on_delete=models.SET_NULL),
        ),
    ]
