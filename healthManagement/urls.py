from django.urls import path
from .views import get_patients

urlpatterns = [
    path('patients', get_patients),
]