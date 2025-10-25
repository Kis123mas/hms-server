from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import Group
from knox.auth import TokenAuthentication
from datetime import datetime, date
from django.utils import timezone
from utils import APPLICATIONS_USER_MODEL
from .serializers import *
from openai import OpenAI
from django.core.mail import send_mail



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
    }, status=status.HTTP_400_BAD_REQUEST)






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
    }, status=status.HTTP_400_BAD_REQUEST)



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