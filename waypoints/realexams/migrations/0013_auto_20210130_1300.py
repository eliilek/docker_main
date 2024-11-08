# Generated by Django 2.2 on 2021-01-30 19:00

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('realexams', '0012_testquestionordering'),
    ]

    operations = [
        migrations.AlterField(
            model_name='test',
            name='questions',
            field=models.ManyToManyField(blank=True, to='realexams.Question'),
        ),
        migrations.AlterField(
            model_name='test',
            name='students',
            field=models.ManyToManyField(blank=True, to=settings.AUTH_USER_MODEL),
        ),
    ]
