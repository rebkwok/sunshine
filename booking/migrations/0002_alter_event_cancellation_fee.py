# Generated by Django 3.2.8 on 2021-10-28 11:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='event',
            name='cancellation_fee',
            field=models.DecimalField(decimal_places=2, default=0.0, max_digits=8),
        ),
    ]
