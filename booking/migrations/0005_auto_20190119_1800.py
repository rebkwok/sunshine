# Generated by Django 2.0.3 on 2019-01-19 18:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0004_auto_20161004_1405'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='event',
            options={'ordering': ['-date'], 'verbose_name': 'Event'},
        ),
        migrations.AlterField(
            model_name='event',
            name='event_type',
            field=models.CharField(choices=[('workshop', 'Workshop'), ('regular_session', 'Regular Timetabled Session')], default='workshop', max_length=255),
        ),
    ]