# Generated by Django 4.1.1 on 2023-03-24 16:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("timetable", "0007_remove_timetablesession_alt_cost_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="timetablesession",
            name="cancellation_period",
            field=models.PositiveIntegerField(default=24),
        ),
    ]
