# Generated by Django 3.2.8 on 2021-10-28 11:18

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('timetable', '0002_membershipcategory_colour'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='membershipcategory',
            options={'verbose_name_plural': 'membership categories'},
        ),
        migrations.AlterModelOptions(
            name='sessiontype',
            options={'verbose_name': 'class type', 'verbose_name_plural': 'class types'},
        ),
        migrations.AlterField(
            model_name='sessiontype',
            name='index',
            field=models.PositiveIntegerField(blank=True, help_text='Determines order class types are displayed on homepage', null=True),
        ),
        migrations.AlterField(
            model_name='timetablesession',
            name='alt_cost',
            field=models.DecimalField(decimal_places=2, default=8, help_text='Cost for additional session for members', max_digits=8, verbose_name='Member cost'),
        ),
        migrations.AlterField(
            model_name='timetablesession',
            name='cancellation_fee',
            field=models.DecimalField(decimal_places=2, default=0.0, max_digits=8),
        ),
        migrations.AlterField(
            model_name='timetablesession',
            name='cost',
            field=models.DecimalField(decimal_places=2, default=8, help_text='Cost for non-members', max_digits=8),
        ),
        migrations.AlterField(
            model_name='timetablesession',
            name='session_type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='timetable.sessiontype', verbose_name='class type'),
        ),
    ]