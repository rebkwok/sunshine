# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='AboutInfo',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, primary_key=True, verbose_name='ID')),
                ('heading', models.CharField(max_length=255, null=True, blank=True)),
                ('subheading', models.CharField(max_length=255, null=True, blank=True)),
                ('content', models.TextField(verbose_name='Content (note line breaks do not display on the summary page)')),
            ],
            options={
                'verbose_name_plural': 'About page information',
            },
        ),
        migrations.CreateModel(
            name='Achievement',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, primary_key=True, verbose_name='ID')),
                ('category', models.CharField(max_length=255, null=True, blank=True, verbose_name='Comp category/description')),
                ('placing', models.CharField(max_length=255, null=True, blank=True, verbose_name='Placing or other achievement')),
                ('display', models.BooleanField(verbose_name='Display this entry on the About page', default=True)),
            ],
        ),
        migrations.CreateModel(
            name='PastEvent',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, primary_key=True, verbose_name='ID')),
                ('name', models.CharField(max_length=255, verbose_name='Past Competition/Show/Event')),
            ],
        ),
        migrations.AddField(
            model_name='achievement',
            name='event',
            field=models.ForeignKey(to='website.PastEvent'),
        ),
    ]
