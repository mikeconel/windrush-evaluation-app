# urls.py
from django.urls import path, include
from .views import home_view, evaluation_form, download_pdf
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', evaluation_form, name='evaluation_form'),
    path('download-pdf/', download_pdf, name='download_pdf'),
    #path('response/', response.as_view(), name='response'),
    path('home/', home_view, name='home'),  # Streamlit integration home page
]