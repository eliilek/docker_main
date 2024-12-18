# Generated by Django 2.2.7 on 2020-03-11 15:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('realexams', '0003_file'),
    ]

    operations = [
        migrations.AddField(
            model_name='question',
            name='correct_answer_image',
            field=models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name='correct_image', to='realexams.Image'),
        ),
        migrations.AddField(
            model_name='question',
            name='incorrect_answer_1_image',
            field=models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name='incorrect_image_1', to='realexams.Image'),
        ),
        migrations.AddField(
            model_name='question',
            name='incorrect_answer_2_image',
            field=models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name='incorrect_image_2', to='realexams.Image'),
        ),
        migrations.AddField(
            model_name='question',
            name='incorrect_answer_3_image',
            field=models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name='incorrect_image_3', to='realexams.Image'),
        ),
        migrations.AlterField(
            model_name='question',
            name='image',
            field=models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name='q_image', to='realexams.Image'),
        ),
    ]
