# # evaluations/utils/pdf.py
from reportlab.pdfgen import canvas
from io import BytesIO

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
#     p = canvas.Canvas(buffer)
    
#     # PDF Content
#     p.drawString(100, 800, "Windrush Foundation Evaluation Report")
#     y_position = 780
    
#     for response in response_data:
#         p.drawString(100, y_position, f"Q: {response.question.text}")
#         p.drawString(120, y_position-20, f"A: {response.answer}")
#         y_position -= 40
        
#     p.save()
#     buffer.seek(0)
#     return buffer