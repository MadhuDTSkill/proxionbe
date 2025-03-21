# Generated by Django 5.1.1 on 2025-02-15 17:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chats_app', '0006_alter_chatnotes_notes'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='chat',
            options={'ordering': ['-created_at']},
        ),
        migrations.AddField(
            model_name='llmresponse',
            name='is_thoughted',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='llmresponse',
            name='thinked_thoughts',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='llmresponse',
            name='time_taken',
            field=models.FloatField(blank=True, null=True),
        ),
    ]
