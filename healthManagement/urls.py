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
     path('mark_patient_left/<int:appointment_id>', mark_patient_left),
    path('mark_vitals_taken/<int:appointment_id>', mark_vitals_taken),
    
    path('mark_doctor_with_patient/<int:appointment_id>', mark_doctor_with_patient),
    path('mark_doctor_done_with_patient/<int:appointment_id>', mark_doctor_done_with_patient),
    
    # Vital signs endpoints
    path('create_patient_vital', create_patient_vital),
    path('patient_vitals/<int:patient_id>', get_patient_vitals),
    
    # Appointment status management endpoints
    path('confirm_appointment/<int:appointment_id>', confirm_appointment),
    path('cancel_appointment/<int:appointment_id>', cancel_appointment),
    path('terminate_appointment/<int:appointment_id>', terminate_appointment),
    path('update_appointment/<int:appointment_id>', update_appointment),
    
    # Medical Records
    path('medical-records', medical_records_list_create),
    path('patients/<int:patient_id>', get_patient_medical_records),
    
    # Treatment endpoints
    path('medical-records/<int:medical_record_id>/treatments', create_treatment),
    path('medical-records/<int:medical_record_id>', get_medical_record_treatments),
    
    # Surgery placement endpoint
    path('surgery-placements', create_surgery_placement),
    
    # Ward and bed space information
    path('ward-space-info', get_ward_space_info),
    
    # Patient admission
    path('admit-patient', admit_patient),
    path('user-admissions', get_user_admissions),
    

    # Test requests
    path('test-requests', list_test_requests),
    path('test-request-create', create_test_request),


    path('pharmacy-referrals', get_pharmacy_referrals),
    
    # Pharmacy endpoints
    path('drugs', get_drugs),
    
    # Pharmacy referrals
    path('pharmacy-referrals', create_pharmacy_referral),
    
    # Patient users
    path('patients', get_patient_users),
    path('patient-detail/<int:user_id>', get_patient_user_detail),

    path('get-all-drugs', get_drugs),
    
    # Delivered medication treatment endpoints
    path('delivered-medication-treatments', create_delivered_medication_treatment),
    path('delivered-medication-treatments/list', get_delivered_medication_treatments),
    path('delivered-medication-treatments/treatment/<int:treatment_id>', get_delivered_medications_for_treatment),
    path('delivered-medication-treatments/<int:treatment_id>', delete_delivered_treatment),

    path('patient-treatment-history/<int:patient_id>', get_patient_treatment_history),


    path('create-doctor-visit', create_doctor_visit),


    path('doctor-visits/<int:treatment_id>', get_doctor_visits_for_treatment),
    
    # Treatment endpoints
    path('treatments', get_my_medications),

    path('who_administered/<int:delivered_medication_treatment_id>', get_who_administered_for_treatment),

    path('update-pharmacy-referrals/<int:referral_id>', confirm_drug_dispense),
    path('pharmacy-referrals/<int:referral_id>', update_pharmacy_referral_payment),

    path('generate-bulk-sale-id', generate_bulk_sale_id),
    path('get-user-bulk-sale-ids', get_user_bulk_sale_ids),
    path('create-bulk-dispensed-items', create_bulk_dispensed_items),
    path('create-drug-sales', create_drug_sale),
    path('list-drug-sales', list_drug_sales),
    path('drug-sales/<int:pk>', drug_sale_detail),
    path('update-test-request/<int:pk>', update_test_request_payment),
    path('update-drug-sales/<int:pk>', update_drug_sale_payment),
    path('patient-admission-charges/<str:patient_email>', get_patient_admission_charges),
    path('admission-charges', create_admission_charge),
    path('admission-charges/<int:charge_id>', update_admission_charge),
    path('test-types', get_test_types),
    path('payment-methods', get_payment_methods),
]