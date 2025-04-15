# evaluations/models.py
from django.db import models
from django.contrib.auth.models import User  # Add this import


class Question(models.Model):
    SECTION_CHOICES = [
        ('demographic', 'Demographic Information'),
        ('pre_event', 'Pre-Event Questions'),
        ('post_event', 'Post-Event Feedback'),
    ]
    # Add this field
    section_order = models.PositiveIntegerField(
        default=0,
        help_text="Order within the section")

    QUESTION_TYPES = [
        ('MC', 'Multiple Choice'),
        ('SC', 'Single Choice'),
        ('TF', 'True/False'),
        ('TX', 'Text Input'),
        ('RT', 'Rating Scale')
    ]
    

    text = models.TextField()
    question_type = models.CharField(max_length=2, choices=QUESTION_TYPES)
    options = models.JSONField(null=True, blank=True)
    section = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Participant(models.Model):
    GENDER_CHOICES = [('M','Male'),('F','Female'),('NS','Not Specified')]
    ETHNICITY_CHOICES = [
        ('AA','African'),('C','Caribbean'),('B','Black other'),
        ('A','Asian'),('E','European'),('MB','Mixed Black'),
        ('MO','Mixed Other'),('W','White'),('O','Other'),('NS','Not Specified')
    ]

    AGE_RANGES=[('12-17', '12-17 Years'),
        ('18-24', '18-24 Years'),
        ('25-34', '25-34 Years'),  # Added missing range
        ('35-44', '35-44 Years'),
        ('45-54', '45-54 Years'),
        ('55-64', '55-64 Years'),
        ('65-74', '65-74 Years'),
        ('75-89', '75-89 Years'),
        ('90+', '90+ Years')]
 
    REFERRAL_SOURCE_CHOICES = [
        ('social_media', 'Social Media'),
        ('word_of_mouth', 'Word of Mouth'),
        ('email', 'Email'),
        ('printed_media', 'Printed Media'),
        ('tv', 'TV'),
        ('radio', 'Radio'),
        ('other', 'Other')
    ]
    
    
    ACCESSIBILITY_NEEDS = [
    ('no_accessibility_needs', 'No accessibility needs'),
    ('hearing_assistance', 'Hearing assistance (e.g., captions, sign language interpretation)'),
    ('visual_assistance', 'Visual assistance (e.g., screen reader, magnification, Braille materials)'),
    ('mobility_support', 'Mobility support (e.g., wheelchair access, ramps, accessible seating)'),
    ('cognitive_or_neurodiversity', 'Cognitive or neurodiversity support (e.g., clear instructions, sensory-friendly environment)'),
    ('assistive_technology', 'Assistive technology (e.g., speech-to-text software, adaptive keyboards)'),
    ('transportation_assistance', 'Transportation assistance (e.g., accessible parking, shuttle service)'),
    ('dietary_accommodations', 'Dietary accommodations (e.g., food allergies, specialized meals)'),
    ('communication_assistance', 'Communication assistance (e.g., alternative formats, easy-read materials)')
]

    
    
    session_key = models.CharField(max_length=40)
    gender = models.CharField(max_length=2, choices=GENDER_CHOICES, default='NS')
    age = models.CharField(max_length=7,choices=AGE_RANGES, default='18-24')
    #age = models.PositiveIntegerField(null=True)
    ethnicity = models.CharField(max_length=2, choices=ETHNICITY_CHOICES, default='NS')
    country = models.CharField(max_length=50,default='England')
    postcode = models.CharField(max_length=10, default='')  # Add default here
    #accessibility_needs = models.TextField(blank=True)
    accessibility_needs = models.CharField(max_length=100,choices=ACCESSIBILITY_NEEDS,default="No accessibility needs")
    referral_source = models.CharField(max_length=20,choices=REFERRAL_SOURCE_CHOICES,blank=True,default='')
    mailing_list_optin = models.BooleanField(default=False)
    books_requested = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

class Response(models.Model):
    #session_key = models.CharField(max_length=40, default='', null=False)
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE)
    question = models.ForeignKey('Question', on_delete=models.CASCADE)
    answer = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

class EvaluationSession(models.Model):
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE)
    completed = models.BooleanField(default=False)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)


# class Response(models.Model):
#     user = models.ForeignKey(
#         User, 
#         on_delete=models.SET_NULL, 
#         null=True,
#         blank=True  # Allows anonymous submissions
#     )
#     question = models.ForeignKey(Question, on_delete=models.CASCADE)
#     answer = models.JSONField() # Stores diffent answers.
#     session_key = models.CharField(max_length=40, default='', null=False)  # Add this field
#     created_at = models.DateTimeField(auto_now_add=True)

