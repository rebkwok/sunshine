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
                ('id', models.AutoField(primary_key=True, serialize=False, verbose_name='ID', auto_created=True)),
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
                ('id', models.AutoField(primary_key=True, serialize=False, verbose_name='ID', auto_created=True)),
                ('category', models.CharField(max_length=255, verbose_name='Comp category/description', null=True, blank=True)),
                ('placing', models.CharField(max_length=255, verbose_name='Placing or other achievement', null=True, blank=True)),
                ('display', models.BooleanField(verbose_name='Display this entry on the About page', default=True)),
            ],
        ),
        migrations.CreateModel(
            name='PastEvent',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, verbose_name='ID', auto_created=True)),
                ('name', models.CharField(max_length=255, verbose_name='Past Competition/Show/Event')),
            ],
        ),
        migrations.AddField(
            model_name='achievement',
            name='event',
            field=models.ForeignKey(to='website.PastEvent'),
        ),
    ]
