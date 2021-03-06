# -*- coding: utf-8 -*-
# Generated by Django 1.11.3 on 2018-03-01 09:58
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
import mptt.fields


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0020_auto_20170406_1052'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='amountmeasure',
            options={'ordering': ['-id'], 'permissions': (('view_amountmeasure', 'View measure'),)},
        ),
        migrations.AlterModelOptions(
            name='item',
            options={'ordering': ['-id'], 'permissions': (('view_item', 'View item'),)},
        ),
        migrations.AlterModelOptions(
            name='set',
            options={'ordering': ['-id'], 'permissions': (('view_set', 'View item set'),)},
        ),
        migrations.AlterField(
            model_name='item',
            name='location',
            field=mptt.fields.TreeForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='inventory.Location'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='itemproperty',
            name='name',
            field=models.CharField(db_index=True, max_length=200),
        ),
        migrations.AlterField(
            model_name='itemproperty',
            name='value',
            field=models.TextField(db_index=True),
        ),
    ]
