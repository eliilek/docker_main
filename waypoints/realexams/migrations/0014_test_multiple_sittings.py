# Generated by Django 2.2 on 2022-09-15 21:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('realexams', '0013_auto_20210130_1300'),
    ]

    operations = [
        migrations.AddField(
            model_name='test',
            name='multiple_sittings',
            field=models.BooleanField(default=False, verbose_name='Can be done over multiple sittings'),
        ),
    ]
