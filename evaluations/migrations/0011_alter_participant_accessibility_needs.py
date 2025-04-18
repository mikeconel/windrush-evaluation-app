# Generated by Django 4.2.7 on 2025-04-11 12:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('evaluations', '0010_participant_country'),
    ]

    operations = [
        migrations.AlterField(
            model_name='participant',
            name='accessibility_needs',
            field=models.CharField(choices=[('no_accessibility_needs', 'No accessibility needs'), ('hearing_assistance', 'Hearing assistance (e.g., captions, sign language interpretation)'), ('visual_assistance', 'Visual assistance (e.g., screen reader, magnification, Braille materials)'), ('mobility_support', 'Mobility support (e.g., wheelchair access, ramps, accessible seating)'), ('cognitive_or_neurodiversity', 'Cognitive or neurodiversity support (e.g., clear instructions, sensory-friendly environment)'), ('assistive_technology', 'Assistive technology (e.g., speech-to-text software, adaptive keyboards)'), ('transportation_assistance', 'Transportation assistance (e.g., accessible parking, shuttle service)'), ('dietary_accommodations', 'Dietary accommodations (e.g., food allergies, specialized meals)'), ('communication_assistance', 'Communication assistance (e.g., alternative formats, easy-read materials)')], default='No accessibility needs', max_length=100),
        ),
    ]
