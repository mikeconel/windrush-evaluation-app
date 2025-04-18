# Generated by Django 4.2.7 on 2025-04-03 22:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('evaluations', '0003_alter_participant_session_key'),
    ]

    operations = [
        migrations.AddField(
            model_name='participant',
            name='accessibility_needs',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='participant',
            name='books_requested',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='participant',
            name='mailing_list_optin',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='participant',
            name='referral_source',
            field=models.CharField(blank=True, max_length=100),
        ),
    ]
