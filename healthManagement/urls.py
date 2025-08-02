from django.urls import path
from .views import *

urlpatterns = [
    # Profile endpoints
    path('my-info', get_my_profile),
    path('patients', get_patients),
    
    # Appointment endpoints
    path('patient-book-appointment', patient_book_appointment),
    path('doctor-appointments', doctor_appointments),
    path('doctor-update-appointment/<int:appointment_id>', doctor_update_status),
    
    # EMR (Electronic Medical Record) endpoints
    path('get-patient-emr', get_patient_emr),
    path('doc-get-patient-emr/<int:patient_id>', get_patient_emr),
    path('doc-create-patient-emr', create_patient_emr, name='create-patient-emr'),
    path('patient-emr-update/<int:patient_id>', update_patient_emr),
    
    # Patient vitals endpoints
    path('create-patient-vital', create_patient_vital),
    path('update-patient-vital/<int:vital_id>', update_patient_vital),
    
    # Test endpoints
    path('doctor-test-request', create_test_request),
    path('update-test/<int:pk>', update_test_result),
    path('get-all-test-result', get_all_test_results),
    path('get-specific-test-result/<int:test_id>', get_single_test_result),
    
    # Drug inventory endpoints
    path('get-all-drugs', get_all_drugs),
    path('get-specific-drug/<int:drug_id>', get_specific_drug),
    path('update-a-specific-drug/<int:drug_id>', update_drug),


]