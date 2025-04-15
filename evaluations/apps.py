# backend/evaluations/apps.py
from django.apps import AppConfig

class EvaluationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'evaluations'  # Must match directory name
    # Optional: label = 'windrush_evaluations'  # Unique label if needed