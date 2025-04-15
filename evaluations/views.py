# evaluations/views.py
from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from .models import Question, Response, Participant, EvaluationSession
from .utils.pdf import generate_pdf
import json


def home_view(request):
    """Home view redirecting to Streamlit app."""
    return redirect('http://localhost:8501')

def evaluation_form(request):
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Session handling
                if not request.session.session_key:
                    request.session.create()
                
                session_key = request.session.session_key
                
                # Create participant
                participant = Participant.objects.create(
                    session_key=session_key,
                    gender=request.POST.get('gender', 'NS'),
                    ethnicity=request.POST.get('ethnicity', 'NS'),
                    country=request.POST.get('country', 'England'),
                    postcode=request.POST.get('postcode', ''),
                    age=request.POST.get('age','12-17'),
                    accessibility_needs=request.POST.get('accessibility_needs', 'No accessibility needs'),
                    referral_source=request.POST.get('referral_source', '') 
                )
                
                # Process responses
                for key, value in request.POST.items():
                    if key.startswith('q_'):
                        question_id = key.split('_')[1]
                        try:
                            question = Question.objects.get(id=question_id)
                            Response.objects.create(
                                participant=participant,
                                question=question,
                                answer=json.dumps(value)
                            )
                        except Question.DoesNotExist:
                            continue
                
                # Create evaluation session
                EvaluationSession.objects.update_or_create(
                    participant=participant,
                    defaults={'completed': True, 'completed_at': timezone.now()}
                )
                
                return redirect(f'http://localhost:8501/?session_key={session_key}')
        
        except Exception as e:
            return HttpResponse(f"Error processing form: {str(e)}", status=500)
    
    # GET request handling
    #questions = Question.objects.filter(is_active=True).order_by('section_order')
    return render(request, 'evaluations/form.html', {
        'questions': Question.objects.filter(is_active=True).order_by('section'),  # Changed section_order → section
        'gender_choices': Participant.GENDER_CHOICES,
        'ethnicity_choices': Participant.ETHNICITY_CHOICES,
        'age_choices': Participant.AGE_RANGES,
        'accessibility_needs_choices': Participant.ACCESSIBILITY_NEEDS,
        'referral_choices': Participant.REFERRAL_SOURCE_CHOICES
    })

# Add AJAX validation endpoint
@csrf_exempt
def validate_field(request):
    if request.method == 'POST':
        field_name = request.POST.get('field')
        value = request.POST.get('value')
        
        if field_name == 'age':
            # Validate age range selection
            valid_ranges = [choice[0] for choice in Participant.AGE_RANGES]
            if value not in valid_ranges:
                return JsonResponse({
                    'valid': False,
                    'error': 'Please select a valid age range'
                })
        return JsonResponse({'valid': True})

def download_pdf(request, session_key):
    try:
        participant = Participant.objects.get(session_key=session_key)
        responses = Response.objects.filter(participant=participant).select_related('question').values(
            'question__text', 
            'answer'
        )
        
        pdf_buffer = generate_pdf(list(responses))
        response = HttpResponse(pdf_buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="evaluation_{session_key}.pdf"'
        return response
        
    except Participant.DoesNotExist:
        return HttpResponse("Session not found", status=404)


def success_page(request):
    return render(request, 'evaluations/success.html')


# def evaluation_form(request):
#     if request.method == 'POST':
#         responses = []
        
#         # Create session-specific identifier
#         session_key = request.session.session_key or request.session.create()
        
#         # Process all questions
#         for key in request.POST:
#             if key.startswith('q_'):
#                 question_id = key.split('_')[1]
#                 question = Question.objects.get(id=question_id)
#                 answer = request.POST.getlist(key) if question.question_type in ['MC'] else request.POST.get(key)
                
#                 # Create and store response with session link
#                 response = Response.objects.create(
#                     question=question,
#                     answer=json.dumps(answer),
#                     session_key=session_key  # Add this field to your model
#                 )
#                 responses.append({
#                     'question': question.text,
#                     'answer': answer
#                 })

#         # Store responses in session for PDF generation
#         request.session['pdf_responses'] = responses
#         return redirect('download_pdf')
    
#     questions = Question.objects.filter(is_active=True).order_by('section')
#     return render(request, 'evaluations/form.html', {'questions': questions})


# def success_page(request):
#     return render(request, 'evaluations/success.html')

# def download_pdf(request):
#     # Retrieve all responses from session
#     response_data = request.session.get('pdf_responses', [])
    
#     if not response_data:
#         return HttpResponse("No evaluation data found", status=404)
    
#     pdf_buffer = generate_pdf(response_data)
    
#     response = HttpResponse(pdf_buffer, content_type='application/pdf')
#     response['Content-Disposition'] = 'attachment; filename="windrush_evaluation.pdf"'
#     return response



# # evaluations/views.py
# def evaluation_form(request):
#     if request.method == 'POST':
#         responses = []
        
#         # Process form data and collect responses
#         for key in request.POST:
#             if key.startswith('q_'):
#                 question_id = key.split('_')[1]
#                 question = Question.objects.get(id=question_id)
#                 answer = request.POST.getlist(key) if question.question_type in ['MC'] else request.POST.get(key)
                
#                 # Create and store response
#                 response = Response.objects.create(
#                     question=question,
#                     answer=json.dumps(answer))
#                 responses.append({
#                     'question': question.text,
#                     'answer': answer
#                 })

#         # Generate PDF with all responses
#         pdf_buffer = generate_pdf(responses)
#         return redirect('download_pdf', response_id=response.id)
    
#     questions = Question.objects.filter(is_active=True).order_by('section')
#     return render(request, 'evaluations/form.html', {'questions': questions})



# def download_pdf(request, response_id):
#     response = Response.objects.get(id=response_id)
#     pdf_buffer = generate_pdf(response)
    
#     response = HttpResponse(pdf_buffer, content_type='application/pdf')
#     response['Content-Disposition'] = f'attachment; filename="evaluation_{response_id}.pdf"'
#     return response




# from django.shortcuts import render

# # evaluations/views.py
# def evaluation_form(request):
#     active_questions = Question.objects.filter(is_active=True)
    
#     if request.method == 'POST':
#         # Process form data and save responses
#         for question in active_questions:
#             answer = request.POST.get(f'q_{question.id}')
#             Response.objects.create(
#                 question=question,
#                 answer=answer
#             )
#         return redirect('success_page')
    
#     return render(request, 'evaluations/form.html', {'questions': active_questions})
