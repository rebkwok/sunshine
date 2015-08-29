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
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('heading', models.CharField(max_length=255, null=True, blank=True)),
                ('subheading', models.CharField(max_length=255, null=True, blank=True)),
                ('content', models.TextField(verbose_name=b'Content (note line breaks do not display on the summary page)')),
            ],
            options={
                'verbose_name_plural': 'About page information',
            },
        ),
        migrations.CreateModel(
            name='Achievement',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('category', models.CharField(max_length=255, null=True, verbose_name=b'Comp category/description', blank=True)),
                ('placing', models.CharField(max_length=255, null=True, verbose_name=b'Placing or other achievement', blank=True)),
                ('display', models.BooleanField(default=True, verbose_name=b'Display this entry on the About page')),
            ],
        ),
        migrations.CreateModel(
            name='PastEvent',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255, verbose_name=b'Past Competition/Show/Event')),
            ],
        ),
        migrations.AddField(
            model_name='achievement',
            name='event',
            field=models.ForeignKey(to='website.PastEvent'),
        ),
    ]
