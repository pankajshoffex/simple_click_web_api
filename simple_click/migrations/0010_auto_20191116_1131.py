# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2019-11-16 11:31
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('simple_click', '0009_market_is_active'),
    ]

    operations = [
        migrations.AlterField(
            model_name='bet',
            name='result_status',
            field=models.IntegerField(choices=[(1, 'Win'), (2, 'Loss'), (3, 'Pending'), (4, 'Cancelled')], default=3),
        ),
        migrations.AlterField(
            model_name='paymenthistory',
            name='payment_type',
            field=models.IntegerField(choices=[(1, 'Deposit'), (2, 'Withdraw'), (3, 'Win'), (4, 'Play'), (5, 'Loss'), (6, 'Cancelled')], default=0),
        ),
        migrations.AlterField(
            model_name='paymenthistory',
            name='transaction_type',
            field=models.IntegerField(choices=[(1, 'Debit'), (1, 'Credit')], default=0),
        ),
    ]
