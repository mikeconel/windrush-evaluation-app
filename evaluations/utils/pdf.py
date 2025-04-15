# evaluations/utils/pdf.py
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

# evaluations/utils/pdf.py
def generate_pdf(response_data):
    buffer = BytesIO()
    p = canvas.Canvas(buffer)
    
    p.drawString(100, 800, "Windrush Foundation Evaluation Report")
    y_position = 780
    
    for item in response_data:
        p.drawString(100, y_position, f"Q: {item['question_text']}")
        answer = item['answer_value']
        if isinstance(answer, list):
            answer = ", ".join(answer)
        p.drawString(120, y_position-20, f"A: {answer}")
        y_position -= 40
    
    p.save()
    buffer.seek(0)
    return buffer

# def generate_pdf(response_data):
#     buffer = BytesIO()
#     p = canvas.Canvas(buffer, pagesize=letter)
    
#     # PDF Header
#     p.setFont("Helvetica-Bold", 16)
#     p.drawString(100, 800, "Windrush Foundation Evaluation Report")
    
#     # Content styling
#     p.setFont("Helvetica", 12)
#     y_position = 780
    
#     for item in response_data:
#         # Question
#         p.drawString(100, y_position, f"Q: {item['question']}")
        
#         # Answer (handle list answers for MC questions)
#         answer = item['answer']
#         if isinstance(answer, list):
#             answer = ", ".join(answer)
#         p.drawString(120, y_position-20, f"A: {answer}")
        
#         y_position -= 40
#         if y_position < 100:  # Handle page breaks
#             p.showPage()
#             y_position = 780
#             p.setFont("Helvetica", 12)

#     p.save()
#     buffer.seek(0)
#     return buffer