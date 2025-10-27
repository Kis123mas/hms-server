from django.urls import path
from .views import (
    get_my_profile, update_profile, get_departments, get_doctors,
    patient_book_appointment, get_patient_appointments, mark_patient_available,
    mark_vitals_taken, mark_doctor_with_patient, mark_doctor_done_with_patient,
    create_patient_vital, get_patient_vitals, confirm_appointment, cancel_appointment,
    mark_patient_left
)

urlpatterns = [
    # Profile endpoints
    path('my-info', get_my_profile),
    path('update-profile', update_profile),
    path('departments', get_departments),
    path('doctors', get_doctors),


    path('book_appointment', patient_book_appointment),
    path('patient_appointments', get_patient_appointments),
    path('mark_available/<int:appointment_id>', mark_patient_available),
     path('mark_patient_left/<int:appointment_id>', mark_patient_left),
    path('mark_vitals_taken/<int:appointment_id>', mark_vitals_taken),
    
    path('mark_doctor_with_patient/<int:appointment_id>', mark_doctor_with_patient),
    path('mark_doctor_done_with_patient/<int:appointment_id>', mark_doctor_done_with_patient),
    
    # Vital signs endpoints
    path('create_patient_vital', create_patient_vital),
    path('patient_vitals/<int:patient_id>/', get_patient_vitals),
    
    # Appointment status management endpoints
   
    path('confirm_appointment/<int:appointment_id>', confirm_appointment),
    path('cancel_appointment/<int:appointment_id>', cancel_appointment),
]