# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2019-01-16 17:23
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0008_alter_user_username_max_length'),
        ('simple_click', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, serialize=False, to=settings.AUTH_USER_MODEL)),
                ('account_no', models.CharField(max_length=16)),
                ('account_holder_name', models.CharField(max_length=120)),
                ('bank_name', models.TextField()),
                ('ifsc_code', models.CharField(max_length=50)),
            ],
        ),
    ]
