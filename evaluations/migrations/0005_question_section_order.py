# Generated by Django 4.2.7 on 2025-04-04 01:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('evaluations', '0004_participant_accessibility_needs_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='question',
            name='section_order',
            field=models.PositiveIntegerField(default=0, help_text='Order within the section'),
        ),
    ]
