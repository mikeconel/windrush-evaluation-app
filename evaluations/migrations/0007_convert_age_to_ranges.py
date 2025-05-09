# Generated by Django 4.2.7 on 2025-04-06 14:26
from django.db import migrations

def convert_ages(apps, schema_editor):
    Participant = apps.get_model('evaluations', 'Participant')
    
    # Corrected age mapping with proper syntax
    age_mapping = {
        (12, 17): '12-17',
        (18, 24): '18-24',
        (25, 34): '25-34',
        (35, 44): '35-44',
        (45, 54): '45-54',
        (55, 64): '55-64',
        (65, 74): '65-74',
        (75, 89): '75-89',
        (90, None): '90+'  # Handle 90+ case
    }
    
    for participant in Participant.objects.all():
        try:
            age = int(participant.age)
            for (min_age, max_age), range_str in age_mapping.items():
                if max_age:  # Handle ranges with upper bounds
                    if min_age <= age <= max_age:
                        participant.age = range_str
                        break
                else:  # Handle 90+ case
                    if age >= min_age:
                        participant.age = range_str
                        break
            participant.save()
        except ValueError:
            # Handle existing range values or invalid data
            pass

class Migration(migrations.Migration):
    dependencies = [
        # Reference the previous migration that changed the age field
        ('evaluations', '0006_alter_participant_age'),  
    ]

    operations = [
        migrations.RunPython(convert_ages),
    ]