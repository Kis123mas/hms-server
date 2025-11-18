from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import Group
from knox.auth import TokenAuthentication
from datetime import datetime, date
from django.utils import timezone
from .serializers import *
from rest_framework import status
from .models import *
from django.db.models import Q
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404
from django.db.models import Prefetch
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from accountant.models import Income
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from knox.auth import TokenAuthentication
from django.http import Http404
from rest_framework.exceptions import ValidationError
from datetime import datetime, date
from django.utils import timezone
from utils import APPLICATIONS_USER_MODEL
from .serializers import DrugSaleSerializer, DrugSaleListSerializer, DrugSaleDetailSerializer, AdmissionChargesSerializer, AdmissionWithChargesSerializer, AdmissionChargeUpdateSerializer, AdmissionChargeCreateSerializer
from .models import DrugSale, ReferralDispensedDrugItem, AdmissionCharges, Admission
from django.db.models import Prefetch


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_my_profile(request):
    """
    Get complete profile of authenticated user
    - Returns user details + profile information
    - Works for all user types (patients, doctors, staff)
    """
    user = request.user
    serializer = UserProfileSerializer(user, context={'request': request})
    
    return Response({
        'status': 'success',
        'user': serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['PUT', 'PATCH'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def update_profile(request):
    """
    Update profile of authenticated user
    - Supports partial updates (PATCH) and full updates (PUT)
    - Handles file uploads (profile_picture, document_1-4)
    - Creates profile if it doesn't exist
    """
    user = request.user
    
    # Get or create profile
    profile, created = Profile.objects.get_or_create(user=user)
    
    # Use partial=True for PATCH requests to allow partial updates
    partial = request.method == 'PATCH'
    
    # Log request data for debugging
    print(f"Update Profile - User: {user.email}, Method: {request.method}")
    print(f"Request Data: {request.data}")
    
    # Update profile with request data
    serializer = ProfileSerializer(profile, data=request.data, partial=partial, context={'request': request})
    
    if serializer.is_valid():
        serializer.save()
        
        # Return updated user profile
        user_serializer = UserProfileSerializer(user, context={'request': request})
        
        return Response({
            'status': 'success',
            'message': 'Profile updated successfully',
            'user': user_serializer.data
        }, status=status.HTTP_200_OK)
    
    # Log validation errors for debugging
    print(f"Validation Errors: {serializer.errors}")
    
    return Response({
        'status': 'error',
        'message': 'Failed to update profile',
        'errors': serializer.errors
    })


# Get All Departments
@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_departments(request):
    """
    Get all departments
    Requires authentication via Token
    """
    departments = Department.objects.all().order_by('name')
    serializer = DepartmentSerializer(departments, many=True)
    return Response({
        'status': 'success',
        'count': departments.count(),
        'departments': serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def patient_book_appointment(request):
    """
    Book a new appointment
    Required fields: doctor_id, appointment_date, patient_reason_for_appointment
    """
    if not hasattr(request.user, 'role') or request.user.role.name != 'patient':
        return Response(
            {"error": "Only patients can book appointments."},
            status=status.HTTP_403_FORBIDDEN
        )

    serializer = BookAppointmentSerializer(
        data=request.data,
        context={'request': request}
    )

    if serializer.is_valid():
        appointment = serializer.save()
        
        return Response({
            'status': 'success',
            'message': 'Appointment booked successfully.',
            'appointment_id': appointment.id,
            'appointment_date': appointment.appointment_date,
            'doctor': f"{appointment.doctor.first_name} {appointment.doctor.last_name}",
            'status': appointment.status
        }, status=status.HTTP_201_CREATED)

    return Response({
        'status': 'error',
        'errors': serializer.errors
    })


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_doctors(request):
    """
    Get a list of all doctors
    Optional query parameters:
    - search: Filter doctors by name or email
    - department: Filter by department name
    """
    try:
        # Get all users with role 'doctor'
        doctors = get_user_model().objects.filter(role__name='doctor', is_active=True)
        
        # Apply filters if provided
        search_query = request.query_params.get('search', None)
        department = request.query_params.get('department', None)
        
        if search_query:
            doctors = doctors.filter(
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(email__icontains=search_query)
            )
            
        if department:
            doctors = doctors.filter(profile__department__name__iexact=department)
        
        # Serialize the data
        serializer = DoctorListSerializer(
            doctors, 
            many=True,
            context={'request': request}
        )
        
        return Response({
            'status': 'success',
            'count': len(serializer.data),
            'doctors': serializer.data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_user_admissions(request):
    """
    Get all admissions for the authenticated user
    Returns admission history with detailed information
    """
    try:
        # Get all admissions for the current user
        admissions = Admission.objects.filter(
            patient=request.user
        ).select_related(
            'admitted_by',
            'bed',
            'bed__room',
            'bed__room__ward'
        ).prefetch_related(
            'charges'
        ).order_by('-admission_date')
        
       
        # Serialize the data
        serializer = AdmissionSerializer(
            admissions, 
            many=True,
            context={'request': request}
        )
        
        # Debug: Print serialized data
        print(f"Serialized data: {serializer.data}")

        return Response({
            'status': 'success',
            'count': admissions.count(),
            'admissions': serializer.data
        }, status=status.HTTP_200_OK)

    except Exception as e:
        print(f"Error in get_user_admissions: {str(e)}")
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_patient_appointments(request):
    """
    Get all appointments for the authenticated patient
    """
    try:
        # Debug: Print request user info
        print(f"Request User: {request.user}")
        print(f"User Role: {getattr(request.user, 'role', None)}")
        
        # Verify the user is a patient
        if not hasattr(request.user, 'role') or request.user.role.name != 'patient':
            return Response(
                {"error": "Only patients can view appointments."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Get all appointments for the current user as patient
        appointments = Appointment.objects.filter(
            patient=request.user
        ).select_related(
            'doctor', 
            'doctor__profile', 
            'doctor__profile__department'
        ).order_by('-appointment_date')

        # Serialize the data
        serializer = PatientAppointmentSerializer(
            appointments, 
            many=True,
            context={'request': request}
        )

        return Response({
            'status': 'success',
            'count': appointments.count(),
            'appointments': serializer.data
        }, status=status.HTTP_200_OK)

    except Exception as e:
        # Print the full error traceback
        import traceback
        error_traceback = traceback.format_exc()
        print(f"Error in get_patient_appointments: {str(e)}")
        print(f"Traceback: {error_traceback}")
        
        return Response({
            'status': 'error',
            'message': str(e),
            'traceback': error_traceback
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




@api_view(['PATCH'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def mark_patient_available(request, appointment_id):
    """
    Allow a patient to mark themselves as available for their appointment
    Updates the is_patient_available field to True
    """
    try:
        # Verify the user is a patient
        if not hasattr(request.user, 'role') or request.user.role.name != 'patient':
            return Response(
                {"error": "Only patients can mark themselves as available."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Get the appointment and verify it belongs to the current patient
        try:
            appointment = Appointment.objects.get(
                id=appointment_id,
                patient=request.user
            )
        except Appointment.DoesNotExist:
            return Response(
                {"error": "Appointment not found or you don't have permission to modify it."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Update the is_patient_available field to True
        appointment.is_patient_available = True
        # Use update_fields to ensure the signal properly detects the change
        appointment.save(update_fields=['is_patient_available'])

        return Response({
            'status': 'success',
            'message': 'You have been marked as available for this appointment.',
            'appointment_id': appointment.id,
            'is_patient_available': appointment.is_patient_available,
            'appointment_date': appointment.appointment_date,
            'doctor': f"{appointment.doctor.first_name} {appointment.doctor.last_name}"
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




@api_view(['PATCH'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def mark_patient_left(request, appointment_id):
    """
    Allow a patient to mark themselves as having left the hospital
    Updates the is_patient_available field to False and marks appointment as canceled
    Sends notifications to both doctor and nurse
    """
    try:
        # Verify the user is a patient
        if not hasattr(request.user, 'role') or request.user.role.name != 'patient':
            return Response(
                {"error": "Only patients can mark themselves as having left."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Get the appointment and verify it belongs to the current patient
        try:
            appointment = Appointment.objects.get(
                id=appointment_id,
                patient=request.user
            )
        except Appointment.DoesNotExist:
            return Response(
                {"error": "Appointment not found or you don't have permission to modify it."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check if appointment is already completed or canceled
        if appointment.status in ['completed', 'canceled']:
            return Response(
                {"error": f"Cannot update status of a {appointment.status} appointment."},
                
            )

        # Update the appointment status and patient availability
        appointment.is_patient_available = False
        appointment.status = 'canceled'
        appointment.save(update_fields=['is_patient_available', 'status'])

        # Create notification for doctor
        if appointment.doctor:
            Notification.objects.create(
                title="Patient Left - Appointment Canceled",
                message=f"Patient {request.user.get_full_name()} has left the hospital and their appointment has been canceled.",
                sender=request.user,
                receivers=[appointment.doctor]
            )

        # Create notification for nurse if assigned
        if appointment.nurse:
            Notification.objects.create(
                title="Patient Left - Appointment Canceled",
                message=f"Patient {request.user.get_full_name()} has left the hospital and their appointment has been canceled.",
                sender=request.user,
                receivers=[appointment.nurse]
            )

        return Response({
            'status': 'success',
            'message': 'You have been marked as having left the hospital. Your appointment has been canceled.',
            'appointment_id': appointment.id,
            'status': appointment.get_status_display(),
            'is_patient_available': appointment.is_patient_available,
            'canceled_at': timezone.now().isoformat()
        }, status=status.HTTP_200_OK)

    except Exception as e:
        error_traceback = traceback.format_exc()
        print(f"Error in mark_patient_left: {str(e)}")
        print(f"Traceback: {error_traceback}")
        
        return Response({
            'status': 'error',
            'message': 'Failed to update patient status',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




@api_view(['PATCH'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def mark_vitals_taken(request, appointment_id):
    """
    Allow a nurse to mark vitals as taken for an appointment
    Updates the is_vitals_taken field to True and tracks which nurse took vitals
    """
    try:
        # Verify the user is a nurse
        if not hasattr(request.user, 'role') or request.user.role.name != 'nurse':
            return Response(
                {"error": "Only nurses can mark vitals as taken."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Get the appointment
        try:
            appointment = Appointment.objects.get(id=appointment_id)
        except Appointment.DoesNotExist:
            return Response(
                {"error": "Appointment not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check if the nurse is in the same department as the doctor (optional security check)
        if (hasattr(request.user, 'profile') and request.user.profile and 
            hasattr(appointment.doctor, 'profile') and appointment.doctor.profile and
            request.user.profile.department != appointment.doctor.profile.department):
            return Response(
                {"error": "You can only take vitals for appointments in your department."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Update the is_vitals_taken field to True and track the nurse
        appointment.is_vitals_taken = True
        appointment.nurse = request.user
        # Use update_fields to ensure the signal properly detects the change
        appointment.save(update_fields=['is_vitals_taken', 'nurse'])

        return Response({
            'status': 'success',
            'message': 'Vitals have been marked as taken for this appointment.',
            'appointment_id': appointment.id,
            'is_vitals_taken': appointment.is_vitals_taken,
            'nurse_name': f"{request.user.first_name} {request.user.last_name}",
            'appointment_date': appointment.appointment_date,
            'patient': f"{appointment.patient.first_name} {appointment.patient.last_name}",
            'doctor': f"{appointment.doctor.first_name} {appointment.doctor.last_name}"
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



@api_view(['PATCH'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def mark_doctor_with_patient(request, appointment_id):
    """
    Allow a doctor to mark is_doctor_with_patient as True for an appointment the doctor is already associated to the appointment
    Updates the is_doctor_with_patient field to True and tracks which doctor is with the patient
    """
    try:
        # Verify the user is a doctor
        if not hasattr(request.user, 'role') or request.user.role.name != 'doctor':
            return Response(
                {"error": "Only doctors can mark is_doctor_with_patient as True."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Get the appointment
        try:
            appointment = Appointment.objects.get(id=appointment_id)
        except Appointment.DoesNotExist:
            return Response(
                {"error": "Appointment not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check if the doctor is authorized for this appointment
        # The doctor must be the appointment's doctor OR in the same department as the appointment's doctor
        if request.user != appointment.doctor:
            # If not the appointment's doctor, check department match
            if (hasattr(request.user, 'profile') and request.user.profile and 
                hasattr(appointment.doctor, 'profile') and appointment.doctor.profile and
                request.user.profile.department != appointment.doctor.profile.department):
                return Response(
                    {"error": "You can only mark appointments for your own patients or patients in your department."},
                    status=status.HTTP_403_FORBIDDEN
                )

        # Update the is_doctor_with_patient field to True
        appointment.is_doctor_with_patient = True
        # Use update_fields to ensure the signal properly detects the change
        appointment.save(update_fields=['is_doctor_with_patient'])

        return Response({
            'status': 'success',
            'message': 'Doctor has been marked as with the patient for this appointment.',
            'appointment_id': appointment.id,
            'is_doctor_with_patient': appointment.is_doctor_with_patient,
            'doctor_name': f"{request.user.first_name} {request.user.last_name}",
            'appointment_date': appointment.appointment_date,
            'patient': f"{appointment.patient.first_name} {appointment.patient.last_name}",
            'doctor': f"{appointment.doctor.first_name} {appointment.doctor.last_name}"
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



@api_view(['PATCH'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def mark_doctor_done_with_patient(request, appointment_id):
    """
    Allow a doctor to mark is_doctor_done_with_patient as True for an appointment
    Updates the is_doctor_done_with_patient field to True
    """
    try:
        # Verify the user is a doctor
        if not hasattr(request.user, 'role') or request.user.role.name != 'doctor':
            return Response(
                {"error": "Only doctors can mark is_doctor_done_with_patient as True."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Get the appointment
        try:
            appointment = Appointment.objects.get(id=appointment_id)
        except Appointment.DoesNotExist:
            return Response(
                {"error": "Appointment not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check if the doctor is authorized for this appointment
        # The doctor must be the appointment's doctor OR in the same department as the appointment's doctor
        if request.user != appointment.doctor:
            # If not the appointment's doctor, check department match
            if (hasattr(request.user, 'profile') and request.user.profile and 
                hasattr(appointment.doctor, 'profile') and appointment.doctor.profile and
                request.user.profile.department != appointment.doctor.profile.department):
                return Response(
                    {"error": "You can only mark appointments for your own patients or patients in your department."},
                    status=status.HTTP_403_FORBIDDEN
                )

        # Update the is_doctor_done_with_patient field to True
        appointment.is_doctor_done_with_patient = True
        # Use update_fields to ensure the signal properly detects the change
        appointment.save(update_fields=['is_doctor_done_with_patient'])

        return Response({
            'status': 'success',
            'message': 'Doctor has been marked as done with the patient for this appointment.',
            'appointment_id': appointment.id,
            'is_doctor_done_with_patient': appointment.is_doctor_done_with_patient,
            'doctor_name': f"{request.user.first_name} {request.user.last_name}",
            'appointment_date': appointment.appointment_date,
            'patient': f"{appointment.patient.first_name} {appointment.patient.last_name}",
            'doctor': f"{appointment.doctor.first_name} {appointment.doctor.last_name}"
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def create_patient_vital(request):
    """
    Create vital signs for a patient
    - Only nurses and doctors can record vitals
    - Requires patient_id, appointment_id, and vital sign measurements
    - Updates appointment's is_vitals_taken field and triggers notifications
    """
    try:
        print(f"\n=== Received request to create patient vital ===")
        print(f"User: {request.user.email} (ID: {request.user.id})")
        print(f"Request data: {request.data}")
        
        # Verify the user is a nurse or doctor
        if not hasattr(request.user, 'role') or request.user.role.name not in ['nurse', 'doctor']:
            print("Access denied: User is not a nurse or doctor")
            return Response(
                {"error": "Only nurses and doctors can record patient vitals."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Get patient_id and appointment_id from request data
        patient_id = request.data.get('patient_id')
        appointment_id = request.data.get('appointment_id')
        
        print(f"Patient ID: {patient_id}")
        print(f"Appointment ID: {appointment_id}")
        
        if not patient_id:
            error_msg = "patient_id is required"
            print(f"Validation error: {error_msg}")
            return Response(
                {"error": error_msg},
                
            )

        # Verify patient exists and is actually a patient
        try:
            patient = APPLICATIONS_USER_MODEL.objects.get(
                id=patient_id,
                role__name='patient'
            )
        except APPLICATIONS_USER_MODEL.DoesNotExist:
            return Response(
                {"error": "Patient not found or invalid patient ID."},
                status=status.HTTP_404_NOT_FOUND
            )

        appointment = None
        if appointment_id:
            # Verify appointment exists and belongs to the patient if provided
            try:
                appointment = Appointment.objects.get(
                    id=appointment_id,
                    patient=patient
                )
            except Appointment.DoesNotExist:
                return Response(
                    {"error": "Appointment not found or does not belong to this patient."},
                    status=status.HTTP_404_NOT_FOUND
                )

        # Create vital sign record
        vital_data = {
            'patient': patient.id,
            'temperature_c': request.data.get('temperature_c'),
            'pulse_rate': request.data.get('pulse_rate'),
            'respiratory_rate': request.data.get('respiratory_rate'),
            'systolic_bp': request.data.get('systolic_bp'),
            'diastolic_bp': request.data.get('diastolic_bp'),
            'oxygen_saturation': request.data.get('oxygen_saturation'),
            'weight_kg': request.data.get('weight_kg'),
            'height_cm': request.data.get('height_cm'),
            'notes': request.data.get('notes', '')
        }

        print(f"Vital data to be saved: {vital_data}")
        
        serializer = VitalSignSerializer(data=vital_data, context={'request': request})
        
        if serializer.is_valid():
            print("Vital sign data is valid")
            # Save with the current user as recorded_by
            vital_sign = serializer.save(recorded_by=request.user)
            
# Update appointment's is_vitals_taken field if appointment exists
            if appointment:
                appointment.is_vitals_taken = True
                if request.user.role.name == 'nurse' and not appointment.nurse:
                    appointment.nurse = request.user
                appointment.save(update_fields=['is_vitals_taken', 'nurse'])
                appointment_updated = True
            else:
                appointment_updated = False
            
            # Return the created vital sign with full details
            response_serializer = VitalSignSerializer(vital_sign, context={'request': request})
            
            success_message = f'Vital signs recorded successfully for {patient.first_name} {patient.last_name}.'
            if appointment_updated:
                success_message += ' Notifications sent to doctor and patient.'
                
            return Response({
                'status': 'success',
                'message': success_message,
                'vital_sign': response_serializer.data,
                'appointment_updated': appointment_updated
            }, status=status.HTTP_201_CREATED)
        else:
            print(f"Validation errors: {serializer.errors}")
            return Response({
                'status': 'error',
                'message': 'Invalid data provided.',
                'errors': serializer.errors
            })

    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error in create_patient_vital: {str(e)}\n{error_trace}")
        from django.conf import settings
        return Response({
            'status': 'error',
            'message': 'An error occurred while recording vital signs.',
            'detail': str(e),
            'trace': error_trace if settings.DEBUG else None
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PATCH'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def confirm_appointment(request, appointment_id):
    """
    Allow a doctor to confirm an appointment
    Changes appointment status to 'confirmed'
    Sends notification to the patient who booked the appointment
    """
    try:
        # Verify the user is a doctor
        if not hasattr(request.user, 'role') or request.user.role.name != 'doctor':
            return Response(
                {"error": "Only doctors can confirm appointments."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Get the appointment
        try:
            appointment = Appointment.objects.get(id=appointment_id)
        except Appointment.DoesNotExist:
            return Response(
                {"error": "Appointment not found."},
            )

        # Verify the doctor is authorized for this appointment
        if request.user != appointment.doctor:
            return Response(
                {"error": "You can only confirm your own appointments."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Check if appointment is in pending status
        if appointment.status != 'pending':
            return Response(
                {"error": f"Appointment is already {appointment.status}. Only pending appointments can be confirmed."},
                
            )

        # Update appointment status to confirmed
        appointment.status = 'confirmed'
        appointment.save(update_fields=['status'])

        # Create notification for the patient
        notification = Notification.objects.create(
            sender=request.user,
            title="Appointment Confirmed",
            message=f"Dr. {request.user.first_name} {request.user.last_name} has confirmed your appointment scheduled for {appointment.appointment_date.strftime('%B %d, %Y at %I:%M %p')}."
        )
        notification.receivers.add(appointment.patient)

        # Send WebSocket notification to the patient
        from .signals import send_websocket_notification_to_users, send_refresh_appointment_action
        send_websocket_notification_to_users(notification)
        send_refresh_appointment_action([appointment.patient], appointment.id)

        return Response({
            'status': 'success',
            'message': 'Appointment confirmed successfully. Patient has been notified.',
            'appointment_id': appointment.id,
            'appointment_status': appointment.status,
            'appointment_date': appointment.appointment_date,
            'patient': f"{appointment.patient.first_name} {appointment.patient.last_name}"
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PATCH'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def cancel_appointment(request, appointment_id):
    """
    Allow a doctor to cancel an appointment
    Changes appointment status to 'cancelled'
    Sends notification to the patient who booked the appointment
    """
    try:
        # Verify the user is a doctor
        if not hasattr(request.user, 'role') or request.user.role.name != 'doctor':
            return Response(
                {"error": "Only doctors can cancel appointments."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Get the appointment
        try:
            appointment = Appointment.objects.get(id=appointment_id)
        except Appointment.DoesNotExist:
            return Response(
                {"error": "Appointment not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Verify the doctor is authorized for this appointment
        if request.user != appointment.doctor:
            return Response(
                {"error": "You can only cancel your own appointments."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Check if appointment can be cancelled
        if appointment.status in ['cancelled', 'completed']:
            return Response(
                {"error": f"Appointment is already {appointment.status} and cannot be cancelled."},
                
            )

        # Optional: Get cancellation reason from request
        cancellation_reason = request.data.get('reason', 'No reason provided')

        # Update appointment status to cancelled
        appointment.status = 'cancelled'
        appointment.save(update_fields=['status'])

        # Create notification for the patient
        notification = Notification.objects.create(
            sender=request.user,
            title="Appointment Cancelled",
            message=f"Dr. {request.user.first_name} {request.user.last_name} has cancelled your appointment scheduled for {appointment.appointment_date.strftime('%B %d, %Y at %I:%M %p')}. Reason: {cancellation_reason}"
        )
        notification.receivers.add(appointment.patient)

        # Send WebSocket notification to the patient
        from .signals import send_websocket_notification_to_users, send_refresh_appointment_action
        send_websocket_notification_to_users(notification)
        send_refresh_appointment_action([appointment.patient], appointment.id)

        return Response({
            'status': 'success',
            'message': 'Appointment cancelled successfully. Patient has been notified.',
            'appointment_id': appointment.id,
            'appointment_status': appointment.status,
            'appointment_date': appointment.appointment_date,
            'patient': f"{appointment.patient.first_name} {appointment.patient.last_name}",
            'cancellation_reason': cancellation_reason
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PATCH'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def terminate_appointment(request, appointment_id):
    """
    Terminate an appointment
    Changes appointment status to 'cancelled' and records who terminated it
    Allows authorized staff (doctors, nurses, admins) to terminate appointments
    """
    try:
        # Verify the user has permission to terminate appointments
        user_role = getattr(request.user, 'role', None)
        if not user_role or user_role.name not in ['doctor', 'patient', 'nurse', 'admin']:
            return Response(
                {"error": "Only doctors, nurses, and admins can terminate appointments."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Get the appointment
        try:
            appointment = Appointment.objects.get(id=appointment_id)
        except Appointment.DoesNotExist:
            return Response(
                {"error": "Appointment not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check if appointment can be terminated
        if appointment.status in ['cancelled', 'completed']:
            return Response(
                {"error": f"Appointment is already {appointment.status} and cannot be terminated."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get termination reason from request
        termination_reason = request.data.get('reason', 'No reason provided')

        # Use the serializer to update the appointment
        serializer = AppointmentTerminationSerializer(
            instance=appointment,
            data=request.data,
            partial=True,
            context={'request': request}
        )
        
        if serializer.is_valid():
            updated_appointment = serializer.save()
            
            # Create notification for the patient
            notification = Notification.objects.create(
                sender=request.user,
                title="Appointment Terminated",
                message=f"Your appointment scheduled for {appointment.appointment_date.strftime('%B %d, %Y at %I:%M %p')} has been terminated by {request.user.first_name} {request.user.last_name} ({user_role.name}). Reason: {termination_reason}"
            )
            notification.receivers.add(appointment.patient)
            
            # Also notify the doctor if the terminator is not the doctor
            if user_role.name != 'doctor' or request.user != appointment.doctor:
                doctor_notification = Notification.objects.create(
                    sender=request.user,
                    title="Appointment Terminated",
                    message=f"Appointment with {appointment.patient.first_name} {appointment.patient.last_name} scheduled for {appointment.appointment_date.strftime('%B %d, %Y at %I:%M %p')} has been terminated by {request.user.first_name} {request.user.last_name} ({user_role.name}). Reason: {termination_reason}"
                )
                doctor_notification.receivers.add(appointment.doctor)
            
            # Send WebSocket notifications
            from .signals import send_websocket_notification_to_users, send_refresh_appointment_action
            send_websocket_notification_to_users(notification)
            send_refresh_appointment_action([appointment.patient], appointment.id)
            
            # Also notify the doctor if needed
            if user_role.name != 'doctor' or request.user != appointment.doctor:
                send_websocket_notification_to_users(doctor_notification)
                send_refresh_appointment_action([appointment.doctor], appointment.id)

            return Response({
                'status': 'success',
                'message': 'Appointment terminated successfully. Relevant parties have been notified.',
                'appointment_id': updated_appointment.id,
                'appointment_status': updated_appointment.status,
                'appointment_date': updated_appointment.appointment_date,
                'terminated_by': f"{request.user.first_name} {request.user.last_name} ({user_role.name})",
                'termination_reason': termination_reason
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'status': 'error',
                'message': 'Validation failed',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PATCH'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def update_appointment(request, appointment_id):
    """
    Update an appointment's details
    Allows updating doctor, appointment date, and reason
    Only the patient who booked the appointment can update it
    """
    try:
        # Get the appointment
        try:
            appointment = Appointment.objects.get(id=appointment_id)
        except Appointment.DoesNotExist:
            return Response(
                {"error": "Appointment not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Verify the user is the patient who booked the appointment
        if request.user != appointment.patient:
            return Response(
                {"error": "You can only update your own appointments."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Check if appointment can be updated
        if appointment.status in ['cancelled', 'completed']:
            return Response(
                {"error": f"Appointment is already {appointment.status} and cannot be updated."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Use the serializer to update the appointment
        serializer = AppointmentUpdateSerializer(
            appointment, 
            data=request.data, 
            partial=True
        )
        
        if serializer.is_valid():
            updated_appointment = serializer.save()
            
            # Automatically change status back to pending when appointment is updated
            if updated_appointment.status != 'pending':
                updated_appointment.status = 'pending'
                updated_appointment.save()
            
            # Create notification if doctor was changed
            if 'doctor' in serializer.validated_data and serializer.validated_data['doctor'] != appointment.doctor:
                notification = Notification.objects.create(
                    sender=request.user,
                    title="Appointment Doctor Changed",
                    message=f"Your appointment scheduled for {updated_appointment.appointment_date.strftime('%B %d, %Y at %I:%M %p')} has been reassigned to Dr. {updated_appointment.doctor.first_name} {updated_appointment.doctor.last_name}."
                )
                notification.receivers.add(updated_appointment.patient)
                
                # Send WebSocket notification
                from .signals import send_websocket_notification_to_users
                send_websocket_notification_to_users(notification)
            
            # Create notification if date/time was changed
            if 'appointment_date' in serializer.validated_data:
                notification = Notification.objects.create(
                    sender=request.user,
                    title="Appointment Rescheduled",
                    message=f"Your appointment with Dr. {updated_appointment.doctor.first_name} {updated_appointment.doctor.last_name} has been rescheduled to {updated_appointment.appointment_date.strftime('%B %d, %Y at %I:%M %p')}."
                )
                notification.receivers.add(updated_appointment.patient)
                
                # Send WebSocket notification
                from .signals import send_websocket_notification_to_users
                send_websocket_notification_to_users(notification)

            return Response({
                'status': 'success',
                'message': 'Appointment updated successfully.',
                'appointment_id': updated_appointment.id,
                'appointment_date': updated_appointment.appointment_date,
                'doctor': f"Dr. {updated_appointment.doctor.first_name} {updated_appointment.doctor.last_name}",
                'patient_reason_for_appointment': updated_appointment.patient_reason_for_appointment
            }, status=status.HTTP_200_OK)
        
        return Response({
            'status': 'error',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_patient_vitals(request, patient_id):
    """
    Get all vital signs for a specific patient
    - Accessible by any authenticated user
    - Returns all vital sign records for the specified patient
    - Ordered by most recent first
    - Uses VitalSignSerializer for consistent data formatting
    """
    import traceback
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"Fetching vitals for patient ID: {patient_id}")
        
        # Check if patient exists and is actually a patient
        try:
            patient = APPLICATIONS_USER_MODEL.objects.get(
                id=patient_id,
                role__name='patient'
            )
            logger.info(f"Found patient: {patient.first_name} {patient.last_name}")
        except APPLICATIONS_USER_MODEL.DoesNotExist as e:
            logger.error(f"Patient not found: {str(e)}")
            return Response(
                {"error": "Patient not found or invalid patient ID"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Get all vital signs for this patient with related data
        vitals = VitalSign.objects.filter(
            patient=patient
        ).select_related(
            'patient',
            'recorded_by'
        ).order_by('-recorded_at')
        
        logger.info(f"Found {vitals.count()} vitals for patient {patient_id}")

        try:
            # Serialize the data using the existing VitalSignSerializer
            serializer = VitalSignSerializer(vitals, many=True, context={'request': request})
            
            # Get patient's full name
            patient_name = f"{patient.first_name} {patient.last_name}"
            
            # Prepare last_updated safely
            last_updated = None
            if vitals.exists():
                first_vital = vitals.first()
                if hasattr(first_vital, 'recorded_at') and first_vital.recorded_at is not None:
                    last_updated = first_vital.recorded_at.isoformat()
            
            response_data = {
                'status': 'success',
                'patient': {
                    'id': patient.id,
                    'name': patient_name,
                    'email': patient.email
                },
                'vital_signs': serializer.data,
                'count': len(serializer.data),
                'last_updated': last_updated
            }
            
            logger.info(f"Successfully prepared response for patient {patient_id}")
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error serializing vitals: {str(e)}\n{traceback.format_exc()}")
            raise

    except Exception as e:
        logger.error(f"Error in get_patient_vitals: {str(e)}\n{traceback.format_exc()}")
        return Response({
            'status': 'error',
            'message': 'Failed to retrieve patient vitals',
            'detail': str(e),
            'traceback': traceback.format_exc()
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET', 'POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def medical_records_list_create(request):
    """
    List all medical records or create a new one
    - GET: List all medical records (filterable by patient_id)
    - POST: Create a new medical record
    """
    try:
        if request.method == 'GET':
            # Check if user is a doctor or staff
            if request.user.role.name not in ['doctor', 'admin']:
                return Response(
                    {'error': 'Only doctors and admins can view medical records'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Get query parameters
            patient_id = request.query_params.get('patient_id')
            
            # Start with all records
            records = MedicalRecord.objects.all()
            
            # Filter by patient if specified
            if patient_id:
                records = records.filter(patient_id=patient_id)
            
            # If not admin, only show records created by the doctor
            if request.user.role.name == 'doctor':
                records = records.filter(doctor=request.user)
            
            # Order by most recent first
            records = records.order_by('-date_created')
            
            # Serialize and return
            serializer = MedicalRecordSerializer(
                records, 
                many=True,
                context={'request': request}
            )
            
            return Response({
                'status': 'success',
                'count': len(serializer.data),
                'medical_records': serializer.data
            })
            
        elif request.method == 'POST':
            # Only doctors can create medical records
            if not hasattr(request.user, 'role') or request.user.role.name != 'doctor':
                return Response(
                    {'error': 'Only doctors can create medical records'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Create the medical record
            serializer = MedicalRecordSerializer(
                data=request.data,
                context={'request': request}
            )
            
            if serializer.is_valid():
                medical_record = serializer.save()
                
                # Update the associated appointment's is_medical_history_recorded field
                appointment = medical_record.appointment
                if appointment and not appointment.is_medical_history_recorded:
                    appointment.is_medical_history_recorded = True
                    appointment.save()
                
                return Response({
                    'status': 'success',
                    'message': 'Medical record created successfully',
                    'medical_record': MedicalRecordSerializer(
                        medical_record,
                        context={'request': request}
                    ).data
                }, status=status.HTTP_201_CREATED)
            
            return Response({
                'status': 'error',
                'errors': serializer.errors
            })
    
    except Exception as e:
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_patient_medical_records(request, patient_id):
    """
    Get all medical records for a specific patient
    - Only accessible by the patient themselves or a doctor
    - Returns all medical records for the specified patient
    - Ordered by most recent first
    """
    try:
        # Check if the requesting user is the patient or a doctor/admin
        user_role = getattr(request.user, 'role', None)
        is_authorized = (
            request.user.id == int(patient_id) or 
            (user_role and user_role.name in ['doctor', 'admin'])
        )
        if not is_authorized:
            return Response(
                {'error': 'You do not have permission to view these medical records'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get all medical records for the patient, ordered by most recent first
        medical_records = MedicalRecord.objects.filter(
            patient_id=patient_id
        ).select_related('doctor', 'appointment', 'vital_signs').order_by('-date_created')
        
        # Serialize the data
        serializer = MedicalRecordSerializer(
            medical_records,
            many=True,
            context={'request': request}
        )
        
        return Response({
            'status': 'success',
            'count': len(serializer.data),
            'medical_records': serializer.data
        })
        
    except Exception as e:
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def create_treatment(request, medical_record_id):
    """
    Create a new treatment for a medical record
    - POST: Create a new treatment for a medical record
    """
    try:
        print(f"Received request to create treatment for medical record {medical_record_id}")
        print(f"Request data: {request.data}")
        print(f"Request user: {request.user.id} ({request.user.email})")
        
        # Check if medical record exists
        try:
            medical_record = MedicalRecord.objects.get(id=medical_record_id)
            print(f"Found medical record: {medical_record.id}")
        except MedicalRecord.DoesNotExist:
            print("Medical record not found")
            return Response(
                {"status": "error", "message": "Medical record not found."},
                status=status.HTTP_404_NOT_FOUND
            )
            
        user = request.user
        
        # Only doctors can create treatments
        if not (user.role.name == 'doctor' or user.is_staff):
            print("User is not authorized to create treatments")
            return Response(
                {"status": "error", "message": "Only doctors can create treatments."},
                status=status.HTTP_403_FORBIDDEN
            )
            
        data = request.data.copy()
        data['medical_record_id'] = medical_record_id
        
        # If prescribed_by is not provided, use the requesting doctor
        if 'prescribed_by_id' not in data:
            data['prescribed_by_id'] = user.id
            print(f"Setting prescribed_by to requesting user: {user.id}")
            
        print(f"Creating treatment with data: {data}")
        serializer = TreatmentSerializer(data=data, context={'request': request})
        
        if serializer.is_valid():
            print("Serializer is valid, saving treatment...")
            treatment = serializer.save()
            print(f"Treatment created: {treatment.id}")
            
            # Create notification for the patient
            try:
                Notification.objects.create(
                    sender=user,
                    title="New Treatment Prescribed",
                    message=f"Dr. {user.get_full_name()} has prescribed a new treatment: {treatment.name}",
                ).receivers.add(medical_record.patient)
                print("Notification created for patient")
            except Exception as e:
                print(f"Error creating notification: {str(e)}")
                # Don't fail the request if notification fails
            
            return Response({
                'status': 'success',
                'message': 'Treatment created successfully',
                'treatment': TreatmentSerializer(treatment, context={'request': request}).data
            }, status=status.HTTP_201_CREATED)
            
        print(f"Serializer errors: {serializer.errors}")
        return Response({
            'status': 'error',
            'message': 'Invalid data provided',
            'errors': serializer.errors
        })
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error in create_treatment: {str(e)}")
        print(f"Traceback: {error_trace}")
        return Response({
            'status': 'error',
            'message': 'An error occurred while creating the treatment',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_medical_record_treatments(request, medical_record_id):
    """
    Get all treatments for a specific medical record
    - GET: Returns all treatments for the specified medical record
    - Only accessible by the patient or the doctor who created the record
    """
    try:
        # Get the medical record
        medical_record = get_object_or_404(MedicalRecord, id=medical_record_id)
        
        # Check if the request user is the patient or the doctor who created the record
        if request.user != medical_record.patient and request.user != medical_record.doctor:
            return Response(
                {"status": "error", "message": "You don't have permission to view these treatments"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get all treatments for the medical record
        treatments = Treatment.objects.filter(medical_record=medical_record).order_by('-date_created')
        
        # Serialize the treatments
        serializer = TreatmentSerializer(treatments, many=True, context={'request': request})
        
        return Response({
            "status": "success",
            "count": len(serializer.data),
            "treatments": serializer.data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {"status": "error", "message": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )




@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def create_surgery_placement(request):
    """
    Create a new surgery placement
    - POST: Create a new surgery placement for a treatment of type 'surgery'
    - Required fields: treatment_id, medical_record_id, surgery_type, scheduled_date
    - Optional fields: surgeon_id, notes
    """
    try:
        # Only doctors can create surgery placements
        if not hasattr(request.user, 'role') or request.user.role.name != 'doctor':
            return Response(
                {"status": "error", "message": "Only doctors can create surgery placements"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Add the surgeon_id from the request user if not provided
        data = request.data.copy()
        if 'surgeon_id' not in data:
            data['surgeon_id'] = request.user.id
            
        # If patient_id is not provided, try to get it from the medical record
        if 'patient_id' not in data and 'medical_record_id' in data:
            try:
                medical_record = MedicalRecord.objects.get(id=data['medical_record_id'])
                data['patient_id'] = medical_record.patient_id
            except MedicalRecord.DoesNotExist:
                pass
        
        # Validate and create the surgery placement
        serializer = SurgeryPlacementSerializer(data=data, context={'request': request})
        
        if serializer.is_valid():
            # Get the validated data
            medical_record = serializer.validated_data.get('medical_record_id')
            treatment = serializer.validated_data.get('treatment_id')
            patient = serializer.validated_data.get('patient_id')
            
            # Validate medical record exists
            if not medical_record:
                return Response(
                    {"status": "error", "message": "Medical record not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Validate treatment is of type 'surgery'
            if not treatment or treatment.treatment_type != 'surgery':
                return Response(
                    {"status": "error", "message": "The specified treatment is not a surgery type"},
                    
                )
            
            # Validate treatment belongs to the medical record
            if treatment.medical_record != medical_record:
                return Response(
                    {"status": "error", "message": "The treatment does not belong to the specified medical record"},
                    
                )
                
            # Validate patient matches medical record's patient if both are provided
            if patient and patient != medical_record.patient:
                return Response(
                    {"status": "error", "message": "The specified patient does not match the medical record's patient"},
                  
                )
            
            # Save the surgery placement
            surgery_placement = serializer.save()
            
            # Update the treatment status to 'in_progress' if it's 'pending'
            if treatment.status == 'pending':
                treatment.status = 'in_progress'
                treatment.save()
            
            # Create a notification for the patient
            try:
                Notification.objects.create(
                    sender=request.user,
                    title="Surgery Scheduled",
                    message=f"A surgery has been scheduled for you on {surgery_placement.scheduled_date.strftime('%B %d, %Y')}.",
                ).receivers.add(medical_record.patient)
            except Exception as e:
                # Log the error but don't fail the request
                print(f"Failed to create notification: {str(e)}")
            
            return Response({
                "status": "success",
                "message": "Surgery placement created successfully",
                "surgery_placement": SurgeryPlacementSerializer(surgery_placement, context={'request': request}).data
            }, status=status.HTTP_201_CREATED)
        
        return Response({
            "status": "error",
            "message": "Invalid data",
            "errors": serializer.errors
        })
        
    except Exception as e:
        return Response(
            {"status": "error", "message": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )




@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def admit_patient(request):
    """
    Admit a patient to a bed
    Required fields: 
    - bed_id: ID of the bed to admit the patient to
    - patient_id: ID of the patient to admit
    """
    try:
        # Check if user has permission to admit patients
        if request.user.role.name not in ['doctor', 'nurse', 'admin']:
            return Response(
                {'status': 'error', 'message': 'You do not have permission to admit patients'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get patient ID from request
        patient_id = request.data.get('patient_id')
        if not patient_id:
            return Response(
                {'status': 'error', 'message': 'patient_id is required'},
              
            )
        
        # Check if patient exists and get their profile
        try:
            patient = APPLICATIONS_USER_MODEL.objects.get(id=patient_id)
            if hasattr(patient, 'profile') and getattr(patient.profile, 'is_admitted', False):
                return Response(
                    {'status': 'error', 'message': 'This patient is already admitted and has a bed space'},
                    
                )
        except APPLICATIONS_USER_MODEL.DoesNotExist:
            return Response(
                {'status': 'error', 'message': 'Patient not found'},
             
            )
        
        # Proceed with admission
        serializer = AdmitPatientSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            try:
                admission = serializer.save()
                return Response(
                    {
                        'status': 'success', 
                        'message': 'Patient admitted successfully',
                        'admission_id': admission.id
                    },
                    status=status.HTTP_201_CREATED
                )
            except Exception as e:
                return Response(
                    {'status': 'error', 'message': str(e)},
                  
                )
        
        return Response(
            {'status': 'error', 'message': 'Invalid data', 'errors': serializer.errors},
          
        )
            
    except Exception as e:
        return Response(
            {'status': 'error', 'message': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )




@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_ward_space_info(request):
    """
    Get information about all wards, rooms, and bed spaces
    Returns:
    - List of wards with their rooms and bed information
    - Available and occupied bed counts
    """
    try:
        # Get all wards with their related rooms and beds
        wards = Ward.objects.prefetch_related(
            'rooms', 
            'rooms__beds'
        ).all()
        
        serializer = WardSpaceSerializer(wards, many=True)
        
        # Calculate total available and occupied beds
        total_available = 0
        total_occupied = 0
        
        for ward in wards:
            for room in ward.rooms.all():
                available = room.beds.filter(is_occupied=False).count()
                total_available += available
                total_occupied += (room.bed_count - available)
        
        return Response({
            'status': 'success',
            'data': serializer.data,
            'summary': {
                'total_wards': len(wards),
                'total_available_beds': total_available,
                'total_occupied_beds': total_occupied,
                'total_beds': total_available + total_occupied
            }
        })
    
    except Exception as e:
        return Response(
            {"status": "error", "message": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )



@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def list_test_requests(request):
    """
    Get all test requests
    """
    try:
        # Get all test requests ordered by most recent
        test_requests = TestRequest.objects.all().select_related(
            'patient', 'requested_by', 'lab_tehnician'
        ).order_by('-created_at')
        
        # Serialize the data
        serializer = TestRequestListSerializer(test_requests, many=True)
        
        return Response({
            'status': 'success',
            'count': len(serializer.data),
            'results': serializer.data
        })
        
    except Exception as e:
        return Response({
            'status': 'error',
            'message': str(e)
        }) 



@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def create_test_request(request):
    """
    Create a new test request (POST only)
    """
    serializer = TestRequestSerializer(data=request.data)
    if serializer.is_valid():
        # Save the test request first
        test_request = serializer.save(requested_by=request.user)
        
        # If there's a medical record associated with this test request,
        # update its requested_for_test field to True
        if test_request.medical_record:
            medical_record = test_request.medical_record
            medical_record.requested_for_test = True
            medical_record.save(update_fields=['requested_for_test'])
            
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors)




@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_patient_users(request):
    """
    Get all patient users with their profile information
    - Returns a list of all users with role 'patient'
    - Includes detailed profile information for each patient
    - Ordered by most recently joined first
    """
    try:
        print("Fetching patient users...")
        
        # Get the patient role group
        from django.contrib.auth.models import Group
        try:
            patient_group = Group.objects.get(name='patient')
        except Group.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Patient role group does not exist. Please create a "patient" group in the admin.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Get users with the patient role
        patients = APPLICATIONS_USER_MODEL.objects.filter(
            role=patient_group
        ).select_related('profile').order_by('-date_joined')
        
        print(f"Found {patients.count()} patients")
        
        # Serialize the data
        serializer = PatientUserSerializer(patients, many=True)
        
        return Response({
            'status': 'success',
            'count': len(serializer.data),
            'patients': serializer.data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error in get_patient_users: {str(e)}\n{error_trace}")
        
        return Response({
            'status': 'error',
            'message': str(e),
            'trace': error_trace if settings.DEBUG else None
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)





@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_patient_user_detail(request, user_id):
    """
    Get detailed profile and admission information for a specific patient user
    - Returns basic user info, profile details, and current admission status
    - Only returns users with 'patient' role
    - Returns 404 if patient not found or not a patient
    """
    try:
        # Get the patient role group
        try:
            patient_group = Group.objects.get(name='patient')
        except Group.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Patient role group does not exist. Please create a "patient" group in the admin.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Get the specific user and verify they are a patient with related data
        try:
            from django.utils import timezone
            today = timezone.now().date()
            
            # Get patient with profile and current admission data
            patient = APPLICATIONS_USER_MODEL.objects.filter(
                id=user_id,
                role=patient_group
            ).select_related('profile').first()
            
            if not patient:
                return Response({
                    'status': 'error',
                    'message': 'Patient not found or is not a valid patient user.'
                }, status=status.HTTP_404_NOT_FOUND)
                
            # Get current admission if any
            current_admission = patient.admissions.filter(
                status='active'
            ).select_related('bed', 'bed__room', 'bed__room__ward').first()
            
            # Prepare admission data
            admission_data = None
            if current_admission:
                admission_data = {
                    'admission_date': current_admission.admission_date,
                    'ward': {
                        'id': current_admission.bed.room.ward.id,
                        'name': current_admission.bed.room.ward.name,
                        'description': current_admission.bed.room.ward.description
                    },
                    'room': {
                        'id': current_admission.bed.room.id,
                        'name': current_admission.bed.room.name,
                        'description': current_admission.bed.room.description
                    },
                    'bed': {
                        'id': current_admission.bed.id,
                        'name': f"{current_admission.bed.room.name} - Bed {current_admission.bed.id}",
                        'is_occupied': current_admission.bed.is_occupied
                    }
                }
            
            # Prepare patient data
            patient_data = {
                'id': patient.id,
                'email': patient.email,
                'first_name': patient.first_name,
                'last_name': patient.last_name,
                'profile': {
                    'phone_number': patient.profile.phone_number if hasattr(patient, 'profile') else None,
                    'date_of_birth': patient.profile.date_of_birth if hasattr(patient, 'profile') else None,
                    'gender': patient.profile.gender if hasattr(patient, 'profile') else None,
                    'blood_group': patient.profile.blood_group if hasattr(patient, 'profile') else None,
                    'genotype': patient.profile.genotype if hasattr(patient, 'profile') else None,
                    'address': patient.profile.address if hasattr(patient, 'profile') else None,
                    'emergency_contact': patient.profile.emergency_contact if hasattr(patient, 'profile') else None,
                    'profile_picture': request.build_absolute_uri(patient.profile.profile_picture.url) if hasattr(patient, 'profile') and patient.profile.profile_picture else None
                },
                'admission': admission_data
            }
            
            # Return the response in the expected format
            return Response({
                'status': 'success',
                'data': patient_data
            }, status=status.HTTP_200_OK)
            
        except APPLICATIONS_USER_MODEL.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Patient not found or is not a valid patient user.'
            }, status=status.HTTP_404_NOT_FOUND)
            
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error in get_patient_user_detail: {str(e)}\n{error_trace}")
        
        return Response({
            'status': 'error',
            'message': 'An error occurred while fetching patient details.',
            'details': str(e) if settings.DEBUG else None
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)





@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def create_pharmacy_referral(request):
    """
    Create a new pharmacy referral
    Required fields:
    - patient_id: ID of the patient
    - medical_record_id: ID of the medical record
    - referred_by_id: ID of the doctor making the referral
    - drug_ids: List of drug IDs to include in the referral
    - reason: Reason for the referral
    Optional fields:
    - pharmacist_id: ID of the pharmacist (can be assigned later)
    """
    print(f"User: {request.user} (ID: {request.user.id})")
    print(f"Request data: {request.data}")

    if request.method == 'POST':
        try:
            data = request.data.copy()
            print(f"\nRaw request data: {data}")
            
            # Log data types
            print("\nData types:")
            for key, value in data.items():
                print(f"  {key}: {value} (type: {type(value).__name__})")
            
            # Validate required fields
            required_fields = ['patient_id', 'medical_record_id', 'referred_by_id', 'drug_ids', 'reason']
            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                error_msg = f"Missing required fields: {', '.join(missing_fields)}"
                print(f"\nValidation error: {error_msg}")
                return Response({
                    'status': 'error',
                    'message': error_msg
                })
            
            # Convert IDs to integers if they're strings
            id_fields = ['patient_id', 'medical_record_id', 'referred_by_id', 'pharmacist_id']
            for field in id_fields:
                if field in data and data[field] is not None and isinstance(data[field], str):
                    try:
                        data[field] = int(data[field])
                        print(f"Converted {field} to int: {data[field]}")
                    except (ValueError, TypeError) as e:
                        error_msg = f"Invalid {field}: {e}"
                        print(f"\n{error_msg}")
                        return Response({
                            'status': 'error',
                            'message': f'{field} must be a valid number'
                        })
            
            # Ensure drug_ids is a list
            if 'drug_ids' in data and isinstance(data['drug_ids'], str):
                try:
                    import json
                    data['drug_ids'] = json.loads(data['drug_ids'])
                except json.JSONDecodeError:
                    return Response({
                        'status': 'error',
                        'message': 'drug_ids must be a valid JSON array'
                    })
            
            print("\nCreating serializer with data:", data)
            serializer = PharmacyReferralSerializer(data=data, context={'request': request})
            
            if serializer.is_valid():
                print("\nSerializer is valid")
                print("Validated data:", serializer.validated_data)
                
                try:
                    referral = serializer.save()
                    print(f"\nPharmacyReferral created successfully with ID: {referral.id}")
                    
                    # Get the updated serializer with all fields
                    response_serializer = PharmacyReferralSerializer(referral)
                    
                    response_data = {
                        'status': 'success',
                        'message': 'Pharmacy referral created successfully',
                        'referral': response_serializer.data
                    }
                    
                    print("\nSending success response")
                    return Response(response_data, status=status.HTTP_201_CREATED)
                    
                except Exception as e:
                    error_msg = f"Error in serializer.save(): {str(e)}"
                    print(f"\n!!! {error_msg} !!!")
                    print("Traceback:", traceback.format_exc())
                    return Response({
                        'status': 'error',
                        'message': f'Failed to create pharmacy referral: {str(e)}'
                    })
            else:
                error_msg = f"Serializer validation failed: {serializer.errors}"
                print(f"\n!!! {error_msg} !!!")
                print("Data that caused error:", data)
                return Response({
                    'status': 'error',
                    'message': 'Validation failed',
                    'errors': serializer.errors
                })
                
        except Exception as e:
            error_msg = f"Unhandled exception: {str(e)}"
            print(f"\n!!! {error_msg} !!!")
            print("Traceback:", traceback.format_exc())
            return Response({
                'status': 'error',
                'message': 'An unexpected error occurred',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return Response({
        'status': 'error',
        'message': 'Only POST method is allowed'
    }, status=status.HTTP_405_METHOD_NOT_ALLOWED)






@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def create_delivered_medication_treatment(request):
    """
    Create a delivered medication treatment record
    - Only doctors can create delivered medication treatments
    - Requires treatment_id, medical_record_id, drug_id, and treatment details
    """
    try:
        
        # Check if user is a doctor
        if not hasattr(request.user, 'role') or request.user.role.name != 'doctor':
            return Response({
                'status': 'error',
                'message': 'Only doctors can create delivered medication treatments',
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Initialize serializer
        serializer = MedicationTreatmentSerializer(
            data=request.data,
            context={'request': request}
        )
        
        # Validate and save
        if not serializer.is_valid():
            return Response({
                'status': 'error',
                'message': 'Validation failed',
                'errors': serializer.errors
            })
        
        delivered_treatment = serializer.save()
        
        return Response({
            'status': 'success',
            'message': 'Delivered medication treatment created successfully',
            'data': MedicationTreatmentSerializer(delivered_treatment, context={'request': request}).data
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        print(f"[ERROR] Unhandled exception: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return Response({
            'status': 'error',
            'message': 'An unexpected error occurred',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_delivered_medications_for_treatment(request, treatment_id):
    """
    Get all delivered medication treatments for a specific treatment
    - Returns a list of all delivered medications for the specified treatment
    - Only requires authentication, no additional permission checks
    """
    try:
        # Get all delivered treatments for this treatment
        delivered_treatments = DeliveredMedicationTreatment.objects.filter(
            treatment_id=treatment_id
        ).select_related('drug', 'prescribed_by').order_by('-date_created')
        
        # Serialize the data
        serializer = DeliveredMedicationTreatmentSerializer(
            delivered_treatments,
            many=True,
            context={'request': request}
        )
        
        return Response({
            'status': 'success',
            'count': len(serializer.data),
            'treatment_id': treatment_id,
            'delivered_medications': serializer.data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        print(f"[ERROR] Unhandled exception: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return Response({
            'status': 'error',
            'message': 'An unexpected error occurred',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_delivered_medication_treatments(request):
    # For doctors, show all records (or filter by patient if needed)
    if hasattr(request.user, 'role') and request.user.role.name == 'doctor':
        queryset = DeliveredMedicationTreatment.objects.all()
    # For patients, only show their own records
    elif hasattr(request.user, 'role') and request.user.role.name == 'patient':
        queryset = DeliveredMedicationTreatment.objects.filter(
            medical_record__patient__user=request.user
        )
    else:
        return Response({
            'status': 'error',
            'message': 'You do not have permission to view these records'
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Apply any filters from query parameters
    medical_record_id = request.query_params.get('medical_record_id')
    if medical_record_id:
        queryset = queryset.filter(medical_record_id=medical_record_id)
    
    treatment_id = request.query_params.get('treatment_id')
    if treatment_id:
        queryset = queryset.filter(treatment_id=treatment_id)
    
    # Optimize queries
    queryset = queryset.select_related(
        'treatment',
        'medical_record',
        'medical_record__patient',
        'drug',
        'prescribed_by'
    ).order_by('-date_created')
    
    # Serialize and return the data
    serializer = MedicationTreatmentSerializer(queryset, many=True, context={'request': request})
    
    return Response({
        'status': 'success',
        'count': len(serializer.data),
        'data': serializer.data
    })





@api_view(['DELETE'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def delete_delivered_treatment(request, treatment_id):
    try:
        # Get the treatment to be deleted
        treatment = DeliveredMedicationTreatment.objects.get(id=treatment_id)
        
        # Optional: Add permission check if needed
        # if treatment.doctor != request.user:
        #     return Response({
        #         'status': 'error',
        #         'message': 'You do not have permission to delete this treatment'
        #     }, status=status.HTTP_403_FORBIDDEN)
        
        treatment.delete()
        
        return Response({
            'status': 'success',
            'message': 'Treatment deleted successfully'
        }, status=status.HTTP_200_OK)
        
    except DeliveredMedicationTreatment.DoesNotExist:
        return Response({
            'status': 'error',
            'message': 'Treatment not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'status': 'error',
            'message': str(e)
        })

    



# generate view code to get all drugs
@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_drugs(request):
    """
    Get all drugs
    """
    drugs = Drug.objects.all()
    serializer = DrugSerializer(drugs, many=True)
    return Response({
        'status': 'success',
        'count': drugs.count(),
        'data': serializer.data
    }, status=status.HTTP_200_OK)






@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_patient_treatment_history(request, patient_id):
    """
    Get medical records for a patient
    Accessible by any authenticated user
    """
    try:
        # Get the patient
        patient = get_object_or_404(get_user_model(), id=patient_id, role__name='patient')
        
        # Get all medical records for the patient using patient_id
        medical_records = MedicalRecord.objects.filter(
            patient_id=patient_id
        ).select_related(
            'patient',
            'doctor'
        ).prefetch_related(
            'treatments'
        ).order_by('-date_created')  # Changed from 'created_at' to 'date_created'
        
        # Serialize the data
        serializer = PatientTreatmentHistorySerializer(medical_records, many=True, context={'request': request})
        
        return Response({
            'status': 'success',
            'data': serializer.data
        })
        
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return Response({
            'status': 'error',
            'message': str(e)
        })




@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def create_doctor_visit(request):
    serializer = DoctorVisitCreateSerializer(
        data=request.data,
        context={'request': request}
    )
    
    if serializer.is_valid():
        visit = serializer.save()
        return Response({
            'status': 'success',
            'message': 'Doctor visit created successfully',
            'data': {
                'id': visit.id,
                'doctor_id': visit.doctor_id,
                'patient_id': visit.patient_id,
                'treatment_id': visit.delivered_medication_treatment_id,
                'visit_date': visit.visit_date,
                'observation': visit.observation,
                'note': visit.note
            }
        }, status=status.HTTP_201_CREATED)
    
    return Response({
        'status': 'error',
        'message': 'Invalid data',
        'errors': serializer.errors
    })




@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_doctor_visits_for_treatment(request, treatment_id):
    try:
        # Verify the treatment exists
        treatment = DeliveredMedicationTreatment.objects.get(id=treatment_id)
        
        # Get all visits for this treatment
        visits = DoctorVisit.objects.filter(
            delivered_medication_treatment=treatment
        ).select_related('doctor').order_by('-visit_date', '-visit_time')
        
        serializer = DoctorVisitListSerializer(visits, many=True)
        
        return Response({
            'status': 'success',
            'count': visits.count(),
            'data': serializer.data
        })
        
    except DeliveredMedicationTreatment.DoesNotExist:
        return Response({
            'status': 'error',
            'message': 'Treatment not found'
        })
    except Exception as e:
        return Response({
            'status': 'error',
            'message': str(e)
        })

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_my_medications(request):
    """
    Get all treatments from the Treatment model
    - Returns a list of all treatments
    - Includes treatment details and status
    """
    try:
        # Get all treatments
        treatments = Treatment.objects.all()
        
        # Serialize the data
        serializer = PatientMedicationSerializer(treatments, many=True)
        
        return Response({
            'status': 'success',
            'count': len(serializer.data),
            'treatments': serializer.data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'status': 'error',
            'message': str(e)
        })






@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_who_administered_for_treatment(request, delivered_medication_treatment_id):
    """
    Get all who_administered records for a specific delivered medication treatment
    - Returns a list of all who_administered records with nurse details
    - Only requires authentication
    """
    try:
        # Get all who_administered records with related user data
        who_administered_list = who_administered.objects.filter(
            delivered_medication_treatment_id=delivered_medication_treatment_id
        ).select_related('user').order_by('-created_at')
        
        # Prepare response data with nurse name
        response_data = [{
            'id': record.id,
            'nurse_name': f"{record.user.first_name} {record.user.last_name}",
            'nurse_id': record.user.id,
            'nurse_email': record.user.email,
            'preobservation': record.preobservation,
            'postobservation': record.postobservation,
            'nurse_administered': record.nurse_administered,
            'patient_received': record.patient_received,
            'administered_at': record.created_at.isoformat(),
            'last_updated': record.last_updated.isoformat()
        } for record in who_administered_list]
        
        return Response({
            'status': 'success',
            'count': len(response_data),
            'delivered_medication_treatment_id': delivered_medication_treatment_id,
            'administered_records': response_data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        print(f"[ERROR] Unhandled exception: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return Response({
            'status': 'error',
            'message': 'An unexpected error occurred',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)







@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_pharmacy_referrals(request):
    """
    Get all pharmacy referrals
    """
    referrals = PharmacyReferral.objects.all().prefetch_related(
        'referral_dispensed_items__drug'
    )
    serializer = PharmacyReferralListSerializer(referrals, many=True)
    return Response({
        'status': 'success',
        'count': len(serializer.data),  # Use len() on the serialized data
        'data': serializer.data
    }, status=status.HTTP_200_OK)






# In views.py
@api_view(['PATCH'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def confirm_drug_dispense(request, referral_id):
    """
    Endpoint for pharmacy to confirm drug dispensation
    Required: User must be authenticated and have pharmacy role
    Updates: have_pharmacist_despensed and pharmacist fields
    """
    try:
        # Get the referral
        referral = get_object_or_404(PharmacyReferral, id=referral_id)
        
        # Check if the user has pharmacy role
        if not request.user.role or request.user.role.name != 'pharmacy':
            return Response(
                {'status': 'error', 'message': 'Only pharmacy staff can confirm dispensation'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Update the referral
        serializer = PharmacyDispenseUpdateSerializer(
            referral,
            data={'have_pharmacist_despensed': True},
            partial=True,
            context={'request': request}
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response({
                'status': 'success',
                'message': 'Drug dispensation confirmed successfully',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        
        return Response({
            'status': 'error',
            'message': 'Validation error',
            'errors': serializer.errors
        })
        
    except Exception as e:
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)






@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def generate_bulk_sale_id(request):
    """
    Generate a new 6-character alphanumeric bulk sale ID
    """
    print(f"Request method: {request.method}")  # Debug: Print request method
    print(f"Request path: {request.path}")      # Debug: Print request path
    print(f"Request headers: {request.headers}") # Debug: Print headers
    
    try:
        # Create a new BulkSaleId - the save() method will generate the code
        bulk_sale = BulkSaleId.objects.create(staff=request.user)
        print(f"Created BulkSaleId: {bulk_sale.id}")  # Debug: Print created ID
        
        # Serialize the response
        serializer = BulkSaleIdSerializer(bulk_sale)
        
        return Response({
            'status': 'success',
            'message': 'Bulk sale ID generated successfully',
            'data': serializer.data
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        print(f"Error in generate_bulk_sale_id: {str(e)}")  # Debug: Print error
        return Response({
            'status': 'error',
            'message': str(e)
        })




@api_view(['GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def get_user_bulk_sale_ids(request):
    """
    Get all valid BulkSaleId records created by the authenticated user
    """
    try:
        # Get all valid bulk sale IDs for the current user
        bulk_sale_ids = BulkSaleId.objects.filter(
            staff=request.user,
            is_valid=True
        ).order_by('-id')  # Order by ID in descending order (newest first)
        
        serializer = BulkSaleIdSerializer(bulk_sale_ids, many=True)
        
        return Response({
            'status': 'success',
            'data': serializer.data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'status': 'error',
            'message': str(e)
        })




@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def create_bulk_dispensed_items(request):
    """
    Create multiple ReferralDispensedDrugItem instances with the same bulk_sale_id
    """
    print("Request data:", request.data)  # Debug: Print the entire request data
    try:
        data = request.data
        bulk_sale_id = data.get('bulk_sale_id')
        items_data = data.get('items', [])
        
        print("bulk_sale_id:", bulk_sale_id)  # Debug: Print bulk_sale_id
        print("items_data:", items_data)      # Debug: Print items data
        
        if not bulk_sale_id:
            return Response({
                'status': 'error',
                'message': 'bulk_sale_id is required'
            })
        
        try:
            bulk_sale = BulkSaleId.objects.get(id=bulk_sale_id)
        except BulkSaleId.DoesNotExist:
            return Response({
                'status': 'error',
                'message': f'BulkSaleId with id {bulk_sale_id} does not exist'
            }, status=status.HTTP_404_NOT_FOUND)
        
        created_items = []
        errors = []
        
        for index, item_data in enumerate(items_data):
            try:
                print(f"Processing item {index}:", item_data)  # Debug: Print each item being processed
                
                if 'drug' not in item_data:
                    raise ValueError("'drug' field is required for each item")
                
                # Validate drug exists
                try:
                    drug = Drug.objects.get(id=item_data['drug'])
                except Drug.DoesNotExist:
                    raise ValueError(f"Drug with id {item_data['drug']} does not exist")
                
                # Create a new item with the bulk_sale_id
                item = ReferralDispensedDrugItem(
                    drug=drug,
                    number_of_cards=item_data.get('number_of_cards', 1),
                    bulk_sale_id=bulk_sale  # Pass the BulkSaleId instance directly
                )
                item.full_clean()  # Validate the model before saving
                item.save()
                
                created_items.append({
                    'id': item.id,
                    'drug': item.drug_id,
                    'number_of_cards': item.number_of_cards,
                    'bulk_sale_id': bulk_sale.id  # Use the ID directly
                })
                
            except Exception as e:
                error_msg = str(e)
                print(f"Error creating item {index}: {error_msg}")  # Debug: Print specific error
                errors.append({
                    'index': index,
                    'error': error_msg,
                    'data': item_data
                })
        
        if errors and not created_items:
            return Response({
                'status': 'error',
                'message': 'Failed to create any items',
                'errors': errors
            })
            
        return Response({
            'status': 'partial_success' if errors else 'success',
            'created_count': len(created_items),
            'created_items': created_items,
            'error_count': len(errors),
            'errors': errors if errors else None
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        print("Unexpected error in create_bulk_dispensed_items:", str(e))  # Debug: Print unexpected errors
        return Response({
            'status': 'error',
            'message': str(e)
        })







@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def create_drug_sale(request):
    """
    Create a new drug sale using DrugSaleSerializer
    Expected JSON format:
    {
        "bulk_sale_id": 1,
        "items": [
            {"drug": 1, "number_of_cards": 1}
        ],
        "customer_name": "John Doe",
        "total_amount": "100.00",
        "amount_paid": "100.00",
        "payment_method": "cash"
    }
    """
    try:
        print("\n=== Incoming Request Data ===")
        print(f"Method: {request.method}")
        print(f"Content-Type: {request.content_type}")
        print(f"Raw data: {request.body}")
        print(f"Parsed data: {request.data}")
        print("==========================\n")
        
        # Create serializer instance with request data and context
        serializer = DrugSaleSerializer(
            data=request.data,
            context={'request': request}  # Pass request for user context
        )
        
        # Validate the data
        is_valid = serializer.is_valid()
        print("\n=== Validation Results ===")
        print(f"Is valid: {is_valid}")
        if not is_valid:
            print(f"Validation errors: {serializer.errors}")
        print("========================\n")
        
        # If valid, save and return success response
        if is_valid:
            drug_sale = serializer.save()
            print(f"Created DrugSale: {drug_sale.id}")
            return Response({
                'status': 'success',
                'message': 'Drug sale created successfully',
                'data': DrugSaleSerializer(drug_sale).data
            }, status=status.HTTP_201_CREATED)
            
        # If validation fails, return errors
        return Response({
            'status': 'error',
            'errors': serializer.errors,
            'received_data': request.data  # Include received data for debugging
        })
        
    except Exception as e:
        import traceback
        print("\n=== Error Details ===")
        print(f"Error: {str(e)}")
        print("Traceback:")
        traceback.print_exc()
        print("==================\n")
        
        return Response({
            'status': 'error',
            'message': str(e),
            'error_type': type(e).__name__
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)






@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def list_drug_sales(request):
    """
    Get all DrugSale records
    """
    try:
        drug_sales = DrugSale.objects.all()
        serializer = DrugSaleListSerializer(drug_sales, many=True)
        return Response({
            'status': 'success',
            'count': len(serializer.data),
            'drug_sales': serializer.data
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def drug_sale_detail(request, pk):
    """
    Get detailed information about a specific DrugSale including dispensed items
    """
    try:
        # Get the drug sale or return 404 if not found
        drug_sale = get_object_or_404(DrugSale, pk=pk)
        
        # Serialize the drug sale with all related data
        serializer = DrugSaleDetailSerializer(drug_sale)
        
        return Response({
            'status': 'success',
            'data': serializer.data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




@api_view(['PATCH'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def update_drug_sale_payment(request, pk):
    """
    Update payment details for a drug sale
    Required fields: amount_paid, payment_method
    """
    try:
        drug_sale = get_object_or_404(DrugSale, pk=pk)
        
        # Only allow accountants to update payments
        if not request.user.role or request.user.role.name != 'accountant':
            return Response(
                {'error': 'Only accounting staff can update payments'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = DrugSalePaymentUpdateSerializer(
            instance=drug_sale,
            data=request.data,
            partial=True
        )
        
        if serializer.is_valid():
            # Set the payment received by the current user
            # Save the payment and get the updated instance
            drug_sale = serializer.save(
                payment_received_by=request.user,
                payment_status='paid' if Decimal(serializer.validated_data['amount_paid']) >= drug_sale.total_amount else 'partial',
                balance=max(0, drug_sale.total_amount - Decimal(serializer.validated_data['amount_paid']))
            )
            
            # Create Income record for the drug sale payment
            try:
                Income.objects.create(
                    reason=f'Drug Sale - {drug_sale.id}',
                    handled_by=request.user,
                    received_from=drug_sale.customer_name or 'Walk-in Customer',
                    payment_method=serializer.validated_data.get('payment_method', 'cash'),
                    amount=float(serializer.validated_data['amount_paid']),
                    description=f'Payment for drug sale ID: {drug_sale.id}'
                )
            except Exception as e:
                # Log the error but don't fail the request
                print(f"Error creating income record: {str(e)}")
            
            return Response({
                'status': 'success',
                'data': DrugSaleDetailSerializer(drug_sale).data
            })
            
        return Response(serializer.errors)
        
    except Exception as e:
        return Response(
            {'error': str(e)},
          
        )






@api_view(['PATCH'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def update_test_request_payment(request, pk):
    """
    Update test request payment status
    Required fields: amount, payment_method
    Sets is_payment_done to True and payment_received_by to current user
    Updates payment status based on amount and test cost
    """
    test_request = get_object_or_404(TestRequest, pk=pk)
    
    # Only allow accountants to update payments
    if not request.user.role or request.user.role.name != 'accountant':
        return Response(
            {'error': 'Only accounting staff can record payments'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = TestRequestPaymentUpdateSerializer(
        test_request,
        data=request.data,
        partial=True
    )
    
    if serializer.is_valid():
        # Get the test type price from the request data or use a default
        test_cost = Decimal(request.data.get('test_cost', '0'))
        
        # Calculate payment status based on amount
        amount_paid = Decimal(str(serializer.validated_data.get('amount', 0)))
        
        
        # Save the test request with updated payment info
        test_request = serializer.save(
            is_payment_done=True,
            payment_received_by=request.user,
        )
        
        # Safely get patient email
        patient_email = "patient@example.com"
        if hasattr(test_request, "patient") and test_request.patient:
            patient_email = getattr(test_request.patient, 'email', 'patient@example.com')
        
        # Safely get test name
        test_name = "Test"
        if hasattr(test_request, "test") and test_request.test and hasattr(test_request.test, "name"):
            test_name = str(test_request.test.name)
        
        # Get payment method safely
        payment_method = getattr(test_request, 'payment_method', 'cash')
        
        # Create Income record for the test payment
        Income.objects.create(
            reason=f'Test Payment - {test_name}',
            handled_by=request.user,
            received_from=patient_email,
            payment_method=payment_method,
            amount=float(amount_paid),
            description=f'Payment for test: {test_name}.'
        )
        
        return Response({
            'status': 'success',
            'message': 'Payment updated successfully',
            'data': serializer.data
        })
    
    return Response({
        'status': 'error',
        'message': 'Validation error',
        'errors': serializer.errors
    })






@api_view(['PATCH'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def update_pharmacy_referral_payment(request, referral_id):
    """
    Update payment status for a pharmacy referral
    Required fields: amount_paid, mode_of_payment
    Only users with 'accountant' role can update payment
    """
    try:
        # Get the referral or return 404 if not found
        referral = get_object_or_404(PharmacyReferral, id=referral_id)
        
        # Check if user has accountant role
        if not request.user.role or request.user.role.name != 'accountant':
            return Response(
                {'status': 'error', 'message': 'Only accounting staff can process payments'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Validate and update the payment
        serializer = PharmacyReferralPaymentUpdateSerializer(
            referral,
            data=request.data,
            context={'request': request},
            partial=True
        )
        
        if serializer.is_valid():
            referral = serializer.save()
            
            # Safely get patient email
            patient_email = "patient@example.com"
            if hasattr(referral, "patient") and referral.patient:
                patient_email = getattr(referral.patient, 'email', 'patient@example.com')
            
            # Create Income record
            Income.objects.create(
                reason=f'Pharmacy Referral Payment - {referral_id}',
                handled_by=request.user,
                received_from=patient_email,
                payment_method=referral.mode_of_payment,
                amount=float(referral.amount_paid or 0),
                description=f'Payment for pharmacy referral. Patient: {patient_email}'
            )
            
            return Response({
                'status': 'success',
                'message': 'Payment updated successfully',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        
        return Response({
            'status': 'error',
            'message': 'Validation error',
            'errors': serializer.errors
        })
        
    except Exception as e:
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)






@api_view(['GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def get_patient_admission_charges(request, patient_email):
    """
    API endpoint to get admission details and charges for a patient by email.
    """
    try:
        # Try to find the patient by email
        patient = APPLICATIONS_USER_MODEL.objects.get(email=patient_email, role__name='patient')
        
        # Get all admissions for the patient
        admissions = Admission.objects.filter(patient=patient).select_related('bed').prefetch_related('charges')
        
        # Serialize the data (will be empty list if no admissions)
        serializer = AdmissionWithChargesSerializer(admissions, many=True)
        
        return Response({
            "patient_id": patient.id,
            "patient_name": f"{patient.first_name} {patient.last_name}",
            "patient_email": patient.email,
            "admissions": serializer.data,
            "message": "No admission records found for this patient." if not admissions.exists() else None
        })
        
    except APPLICATIONS_USER_MODEL.DoesNotExist:
        return Response(
            {"detail": "Patient not found with the provided email."},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {"detail": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )








@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def create_admission_charge(request):
    """
    Create a new admission charge
    Any authenticated user can create an admission charge
    """
    print("\n===== DEBUG: Entering create_admission_charge view =====")
    print(f"Request method: {request.method}")
    print(f"Request data: {request.data}")
    print(f"Request path: {request.path}")
    print(f"Request full path: {request.get_full_path()}")
    print(f"Request META: {request.META.get('PATH_INFO')}")
    print("=" * 50, "\n")
    
    try:
        # Ensure the admission exists
        admission_id = request.data.get('admission')
        print(f"DEBUG: Admission ID from request: {admission_id}")
        
        try:
            admission = Admission.objects.get(id=admission_id)
            print(f"DEBUG: Found admission: {admission}")
        except Admission.DoesNotExist:
            print(f"DEBUG: Admission with ID {admission_id} not found")
            return Response(
                {'status': 'error', 'message': 'Admission not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Set the paid_to field to the current user if not provided
        if 'paid_to' not in request.data:
            request.data['paid_to'] = request.user.id
            print(f"DEBUG: Set paid_to to current user: {request.user.id}")

        serializer = AdmissionChargeCreateSerializer(data=request.data)
        print(f"DEBUG: Serializer data: {request.data}")

        if serializer.is_valid():
            # Save the charge
            charge = serializer.save()
            print(f"DEBUG: Successfully created charge: {charge.id}")
            return Response({
                'status': 'success',
                'message': 'Admission charge created successfully',
                'data': AdmissionChargesSerializer(charge).data
            }, status=status.HTTP_201_CREATED)

        print(f"DEBUG: Serializer errors: {serializer.errors}")
        return Response({
            'status': 'error',
            'errors': serializer.errors
        })

    except Exception as e:
        print(f"DEBUG: Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        return Response(
            {'status': 'error', 'message': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )







@api_view(['PATCH'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def update_admission_charge(request, charge_id):
    """
    Update an existing admission charge
    """
    
    # Set paid_to to authenticated user, override if frontend tries to set it
    request_data = request.data.copy()
    request_data['paid_to'] = request.user.id
    
    try:
        charge = AdmissionCharges.objects.get(id=charge_id)
        serializer = AdmissionChargeUpdateSerializer(
            charge, 
            data=request_data, 
            partial=True
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response({
                'status': 'success',
                'message': 'Charge updated successfully',
                'data': serializer.data
            })
        return Response({
            'status': 'error',
            'errors': serializer.errors
        })
        
    except AdmissionCharges.DoesNotExist:
        return Response(
            {'status': 'error', 'message': 'Charge not found'},
            
        )
    except Exception as e:
        return Response(
            {'status': 'error', 'message': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )






@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_drugs(request):
    """
    Get all drugs
    """
    drugs = Drug.objects.all()
    serializer = DrugSerializer(drugs, many=True)
    return Response({
        'status': 'success',
        'count': drugs.count(),
        'data': serializer.data
    }, status=status.HTTP_200_OK)





