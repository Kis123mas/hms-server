from django.urls import path
from .views import *

urlpatterns = [
    # Profile endpoints
    path('my-info', get_my_profile),
    path('update-profile', update_profile),
    path('departments', get_departments),
    path('doctors', get_doctors),


    path('book_appointment', patient_book_appointment),
    path('patient_appointments', get_patient_appointments),
    path('mark_available/<int:appointment_id>', mark_patient_available),
    path('mark_vitals_taken/<int:appointment_id>', mark_vitals_taken),
    
]