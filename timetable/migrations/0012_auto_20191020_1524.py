# Generated by Django 2.2.6 on 2019-10-20 14:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('timetable', '0011_timetablesession_max_participants'),
    ]

    operations = [
        migrations.AlterField(
            model_name='timetablesession',
            name='membership_category',
            field=models.CharField(blank=True, choices=[('1', 'Pole and hoop classes'), ('2', 'General fitness and conditioning classes'), ('3', 'Open training')], help_text='Specify type of class for membership purposes', max_length=1, null=True),
        ),
    ]