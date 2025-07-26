from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import Group
from knox.auth import TokenAuthentication
from datetime import datetime
from django.utils import timezone
from utils import APPLICATIONS_USER_MODEL
from .serializers import *

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_patients(request):
    """
    Get all users in the 'patient' group
    Requires authentication via Knox Token
    """
    try:
        # Verify the requesting user has appropriate permissions
        if not request.user.is_staff and not request.user.is_superuser:
            return Response(
                {"error": "You don't have permission to view patients"},
                status=status.HTTP_403_FORBIDDEN
            )

        # Get the patient group
        patient_group = Group.objects.get(name='patient')
        
        # Get all active users in the patient group
        patients = APPLICATIONS_USER_MODEL.objects.filter(
            role=patient_group,
            is_active=True
        ).select_related('role')
        
        # Serialize the data
        serializer = PatientUserSerializer(patients, many=True)
        
        return Response({
            'status': 'success',
            'count': patients.count(),
            'patients': serializer.data
        }, status=status.HTTP_200_OK)
    
    except Group.DoesNotExist:
        return Response({
            'status': 'error',
            'message': 'Patient group does not exist. Please create it first.'
        }, status=status.HTTP_404_NOT_FOUND)
    
    except Exception as e:
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def patient_book_appointment(request):
    """
    Book appointment with:
    - Patient auto-set from token
    - Doctor selected by first_name
    - Date in dd-mm-yyyy HH:MM format
    """
    # Verify patient role
    if not request.user.role or request.user.role.name != 'patient':
        return Response(
            {'status': 'error', 'message': 'Only patients can book appointments'},
            status=status.HTTP_403_FORBIDDEN
        )

    # Get and validate doctor
    doctor_first_name = request.data.get('doctor_first_name')
    if not doctor_first_name:
        return Response(
            {'status': 'error', 'message': 'doctor_first_name is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        doctor = request.user.__class__.objects.get(
            first_name__iexact=doctor_first_name,
            role__name='doctor'
        )
    except request.user.__class__.DoesNotExist:
        return Response(
            {'status': 'error', 'message': 'Doctor not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Parse and validate date
    date_str = request.data.get('appointment_date')
    if not date_str:
        return Response(
            {'status': 'error', 'message': 'appointment_date is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        # Parse dd-mm-yyyy HH:MM format
        appointment_date = datetime.strptime(date_str, '%d-%m-%Y %H:%M')
        appointment_date = timezone.make_aware(appointment_date)
        
        if appointment_date <= timezone.now():
            return Response(
                {'status': 'error', 'message': 'Appointment must be in future'},
                status=status.HTTP_400_BAD_REQUEST
            )
    except ValueError:
        return Response(
            {
                'status': 'error', 
                'message': 'Invalid date format. Use dd-mm-yyyy HH:MM (e.g. 20-12-2023 14:30)'
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    # Create appointment
    appointment_data = {
        'patient_id': request.user.id,
        'doctor_id': doctor.id,
        'appointment_date': appointment_date,
        'reason': request.data.get('reason', '')
    }

    serializer = AppointmentSerializer(data=appointment_data)
    if serializer.is_valid():
        serializer.save()
        return Response(
            {
                'status': 'success',
                'message': f'Appointment booked with Dr. {doctor.first_name}',
                'appointment': serializer.data
            },
            status=status.HTTP_201_CREATED
        )
    
    return Response(
        {'status': 'error', 'errors': serializer.errors},
        status=status.HTTP_400_BAD_REQUEST
    )
    """
    Allows patients to book appointments
    - Patient is automatically set from the token
    - Requires selecting a valid doctor
    - Validates appointment date is in future
    """
    # Verify user is a patient
    if not request.user.role or request.user.role.name != 'patient':
        return Response(
            {
                'status': 'error',
                'message': 'Only patients can book appointments'
            },
            status=status.HTTP_403_FORBIDDEN
        )

    # Prepare data with patient automatically set
    appointment_data = request.data.copy()
    appointment_data['patient_id'] = request.user.id

    # Validate required fields
    if 'doctor_id' not in appointment_data:
        return Response(
            {
                'status': 'error',
                'message': 'Doctor ID is required'
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    # Validate doctor exists and is actually a doctor
    try:
        doctor_group = Group.objects.get(name='doctor')
        if not request.user.__class__.objects.filter(
            id=appointment_data['doctor_id'],
            role=doctor_group
        ).exists():
            return Response(
                {
                    'status': 'error',
                    'message': 'Selected doctor is invalid'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
    except Group.DoesNotExist:
        return Response(
            {
                'status': 'error',
                'message': 'Doctor group does not exist'
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    # Validate appointment date
    if 'appointment_date' not in appointment_data:
        return Response(
            {
                'status': 'error',
                'message': 'Appointment date is required'
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        appointment_date = timezone.datetime.fromisoformat(appointment_data['appointment_date'])
        if appointment_date <= timezone.now():
            return Response(
                {
                    'status': 'error',
                    'message': 'Appointment date must be in the future'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
    except (ValueError, TypeError):
        return Response(
            {
                'status': 'error',
                'message': 'Invalid date format. Use ISO format (YYYY-MM-DDTHH:MM:SSZ)'
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    # Create the appointment
    serializer = AppointmentSerializer(data=appointment_data)
    if serializer.is_valid():
        serializer.save()
        return Response(
            {
                'status': 'success',
                'message': 'Appointment booked successfully',
                'appointment': serializer.data
            },
            status=status.HTTP_201_CREATED
        )
    
    return Response(
        {
            'status': 'error',
            'message': 'Invalid data',
            'errors': serializer.errors
        },
        status=status.HTTP_400_BAD_REQUEST
    )
    """
    Allows patients to book appointments
    - Patient is automatically set from the token
    - Requires selecting a valid doctor
    - Validates appointment date is in future
    """
    # Verify user is a patient
    if not request.user.role or request.user.role.name != 'patient':
        return Response(
            {
                'status': 'error',
                'message': 'Only patients can book appointments'
            },
            status=status.HTTP_403_FORBIDDEN
        )

    # Prepare data with patient automatically set
    appointment_data = request.data.copy()
    appointment_data['patient_id'] = request.user.id

    # Validate required fields
    if 'doctor_id' not in appointment_data:
        return Response(
            {
                'status': 'error',
                'message': 'Doctor ID is required'
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    # Validate doctor exists and is actually a doctor
    try:
        doctor_group = Group.objects.get(name='doctor')
        if not request.user.__class__.objects.filter(
            id=appointment_data['doctor_id'],
            role=doctor_group
        ).exists():
            return Response(
                {
                    'status': 'error',
                    'message': 'Selected doctor is invalid'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
    except Group.DoesNotExist:
        return Response(
            {
                'status': 'error',
                'message': 'Doctor group does not exist'
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    # Validate appointment date
    if 'appointment_date' not in appointment_data:
        return Response(
            {
                'status': 'error',
                'message': 'Appointment date is required'
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        appointment_date = timezone.datetime.fromisoformat(appointment_data['appointment_date'])
        if appointment_date <= timezone.now():
            return Response(
                {
                    'status': 'error',
                    'message': 'Appointment date must be in the future'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
    except (ValueError, TypeError):
        return Response(
            {
                'status': 'error',
                'message': 'Invalid date format. Use ISO format (YYYY-MM-DDTHH:MM:SSZ)'
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    # Create the appointment
    serializer = AppointmentSerializer(data=appointment_data)
    if serializer.is_valid():
        serializer.save()
        return Response(
            {
                'status': 'success',
                'message': 'Appointment booked successfully',
                'appointment': serializer.data
            },
            status=status.HTTP_201_CREATED
        )
    
    return Response(
        {
            'status': 'error',
            'message': 'Invalid data',
            'errors': serializer.errors
        },
        status=status.HTTP_400_BAD_REQUEST
    )




@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def doctor_appointments(request):
    """
    Get all appointments for the authenticated doctor
    - Returns past and upcoming appointments
    - Can filter by status or date range
    """
    # Verify user is a doctor
    if not request.user.role or request.user.role.name != 'doctor':
        return Response(
            {'status': 'error', 'message': 'Only doctors can access this endpoint'},
            status=status.HTTP_403_FORBIDDEN
        )

    # Base queryset
    appointments = Appointment.objects.filter(
        doctor=request.user
    ).select_related('patient').order_by('-appointment_date')

    # Optional filters
    status_filter = request.query_params.get('status')
    if status_filter:
        appointments = appointments.filter(status=status_filter.lower())

    date_from = request.query_params.get('from')
    date_to = request.query_params.get('to')
    
    if date_from:
        try:
            from_date = datetime.strptime(date_from, '%d-%m-%Y').date()
            appointments = appointments.filter(appointment_date__date__gte=from_date)
        except ValueError:
            pass

    if date_to:
        try:
            to_date = datetime.strptime(date_to, '%d-%m-%Y').date()
            appointments = appointments.filter(appointment_date__date__lte=to_date)
        except ValueError:
            pass

    # Serialize with patient details
    serializer = DoctorAppointmentSerializer(appointments, many=True)
    
    return Response({
        'status': 'success',
        'count': appointments.count(),
        'appointments': serializer.data
    })




@api_view(['PATCH'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def doctor_update_status(request, appointment_id):
    """
    Allows doctors to update appointment status
    Valid status transitions:
    - pending → confirmed/cancelled
    - confirmed → completed/cancelled
    - cancelled → (cannot be changed)
    - completed → (cannot be changed)
    """
    # Verify doctor role
    if not request.user.role or request.user.role.name != 'doctor':
        return Response(
            {'status': 'error', 'message': 'Only doctors can update appointment status'},
            status=status.HTTP_403_FORBIDDEN
        )

    try:
        appointment = Appointment.objects.get(
            pk=appointment_id,
            doctor=request.user  # Ensure doctor only updates their own appointments
        )
    except Appointment.DoesNotExist:
        return Response(
            {'status': 'error', 'message': 'Appointment not found or not authorized'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Validate requested status
    new_status = request.data.get('status')
    if not new_status:
        return Response(
            {'status': 'error', 'message': 'Status field is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    valid_statuses = [choice[0] for choice in Appointment.STATUS_CHOICES]
    if new_status not in valid_statuses:
        return Response(
            {
                'status': 'error',
                'message': f'Invalid status. Valid choices: {valid_statuses}'
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    # Validate status transition
    status_rules = {
        'pending': ['confirmed', 'cancelled'],
        'confirmed': ['completed', 'cancelled'],
        'cancelled': [],
        'completed': []
    }

    if new_status not in status_rules.get(appointment.status, []):
        return Response(
            {
                'status': 'error',
                'message': f'Cannot change status from {appointment.status} to {new_status}'
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    # Update status
    appointment.status = new_status
    appointment.save()

    return Response({
        'status': 'success',
        'message': f'Appointment status updated to {new_status}',
        'appointment': DoctorAppointmentSerializer(appointment).data
    })




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
    serializer = UserProfileSerializer(user)
    
    return Response({
        'status': 'success',
        'user': serializer.data
    })