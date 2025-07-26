from django.urls import path
from .views import *

urlpatterns = [
    path('my-info', get_my_profile),
    path('patients', get_patients),
    path('patient-book-appointment', patient_book_appointment),
    path('doctor-appointments/', doctor_appointments),
    path('doctor-update-appointment/<int:appointment_id>', doctor_update_status),
]