# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('timetable', '0005_membershipclasslevel'),
    ]

    operations = [
        migrations.AddField(
            model_name='timetablesession',
            name='membership_level',
            field=models.ForeignKey(help_text='Categorise for membership; 1=pole/hoop classes, 2=general fitness/conditioning classes', null=True, to='timetable.MembershipClassLevel'),
        ),
    ]
