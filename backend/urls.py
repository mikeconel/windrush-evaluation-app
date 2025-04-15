"""
URL configuration for backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from evaluations import views
from evaluations.views import home_view, evaluation_form, download_pdf

urlpatterns = [
    path('admin/', admin.site.urls),  # Admin site
    path('', views.evaluation_form, name='evaluation_form'),
    path('success/', views.success_page, name='success_page'),
    path('', evaluation_form, name='evaluation_form'),
    path('download-pdf/<str:session_key>/', download_pdf, name='download_pdf'),
    path('download-pdf/', views.download_pdf, name='download_pdf'),
    path('api/', include('evaluations.urls')),  # Include app-specific URLs
    path('', home_view, name='home'),  # Redirect to home view
]

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', evaluation_form, name='evaluation_form'),
    path('download-pdf/<str:session_key>/', download_pdf, name='download_pdf'),
]


# urlpatterns = [
#     path('admin/', admin.site.urls),
#     path('', views.evaluation_form, name='evaluation_form'),
#     path('success/', views.success_page, name='success_page'),
#     path('download-pdf/', views.download_pdf, name='download_pdf'),
#     #path('download-pdf/<int:response_id>/', views.download_pdf, name='download_pdf'),
# ]

# # backend/urls.py
# from django.urls import path
# from evaluations import views

# urlpatterns = [
#     path('', views.evaluation_form, name='evaluation_form'),
#     path('download-pdf/', views.download_pdf, name='download_pdf'),
#     path('admin/', admin.site.urls),
# ]