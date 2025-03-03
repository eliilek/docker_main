# Generated by Django 5.1.6 on 2025-02-24 18:19

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jakeapp', '0003_alter_activity_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='assessmentquestionresponse',
            name='assessment_section',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='jakeapp.assessmentsection'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='quiz',
            name='activity',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, to='jakeapp.activity'),
        ),
        migrations.AlterField(
            model_name='quiz',
            name='questions',
            field=models.ManyToManyField(blank=True, to='jakeapp.question'),
        ),
    ]
