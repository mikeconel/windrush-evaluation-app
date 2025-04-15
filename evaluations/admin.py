# evaluations/admin.py
from django.contrib import admin
from .models import Question, Response, Participant, EvaluationSession

from django.contrib import admin
from .models import Question

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('text', 'question_type', 'section', 'section_order', 'is_active')
    list_filter = ('question_type', 'section')
    search_fields = ('text',)
    list_editable = ('section_order', 'is_active')
    ordering = ('section', 'section_order')  # New default ordering

    fieldsets = (
        (None, {
            'fields': ('text', 'question_type', 'section')
        }),
        ('Advanced Options', {
            'fields': ('options', 'section_order', 'is_active'),
            'classes': ('collapse',)
        }),
    )

@admin.register(Response)
class ResponseAdmin(admin.ModelAdmin):
    list_display = ('question', 'created_at')
    #'user', 
    list_filter = ('question__section',)

@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ('session_key', 'gender', 'ethnicity','age','country','postcode','accessibility_needs','referral_source','created_at')
    list_filter = ('gender', 'ethnicity','country','age','accessibility_needs','referral_source')
    search_fields = ('session_key','country' ,'postcode')

@admin.register(EvaluationSession)
class EvaluationSessionAdmin(admin.ModelAdmin):
    list_display = ('participant', 'completed', 'started_at', 'completed_at')
    list_filter = ('completed',)