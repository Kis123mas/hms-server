from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from knox.auth import TokenAuthentication
from .models import *
from .serializers import *
from datetime import datetime, timedelta
from django.db.models import Sum, Count
from django.db.models.functions import TruncWeek, TruncMonth, TruncYear
from django.utils import timezone
from utils import APPLICATIONS_USER_MODEL
from django.contrib.auth.models import Group
from django.utils import timezone
from healthManagement.models import *

# Activity tracking helper function
def track_user_action(user, action, model_name, object_id=None, action_taken_on=None, description=""):
    """
    Helper function to track user actions
    """
    try:
        Activity.objects.create(
            action_taken_by=user,
            action_taken_on=action_taken_on,
            action=action,
            model_name=model_name,
            object_id=object_id,
            description=description
        )
    except Exception as e:
        print(f"Error tracking activity: {str(e)}")

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def income_list(request):
    """
    Simple function-based view to list all income records
    """
    try:
        # Track user action
        track_user_action(
            user=request.user,
            action='read',
            model_name='Income',
            description=f"Accountant {request.user.email} viewed income records list"
        )
        
        # Get all income records ordered by most recent first
        incomes = Income.objects.all().order_by('-created_at')
        
        # Serialize the data
        serializer = IncomeSerializer(incomes, many=True)
        
        # Calculate total income
        total_income = sum(income.amount for income in incomes)
        
        # Prepare response
        response_data = {
            'status': 'success',
            'count': len(serializer.data),
            'total_income': total_income,
            'data': serializer.data
        }
        
        return Response(response_data)
    
    except Exception as e:
        return Response(
            {'status': 'error', 'message': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )





@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def expense_list(request):
    """
    Get a list of all expense records
    """
    try:
        # Track user action
        track_user_action(
            user=request.user,
            action='read',
            model_name='Expense',
            description=f"Accountant {request.user.email} viewed expense records list"
        )
        
        # Get all expenses ordered by most recent first
        expenses = Expense.objects.all().order_by('-date', '-created_at')
        serializer = ExpenseSerializer(expenses, many=True)
        
        # Calculate total expenses
        total_expenses = sum(expense.amount for expense in expenses)
        
        return Response({
            'status': 'success',
            'count': len(serializer.data),
            'total_expenses': float(total_expenses),
            'data': serializer.data
        })
        
    except Exception as e:
        return Response(
            {'status': 'error', 'message': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )




@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def create_expense(request):
    """
    Create a new expense record
    """
    try:
        print("\n=== Incoming Request Data ===")
        print(f"Request method: {request.method}")
        print(f"Content-Type: {request.content_type}")
        print(f"Request data: {request.data}")
        
        serializer = CreateExpenseSerializer(
            data=request.data,
            context={'request': request}
        )
        
        print("\n=== Validation Results ===")
        is_valid = serializer.is_valid()
        print(f"Is valid: {is_valid}")
        
        if not is_valid:
            print("Validation errors:", serializer.errors)
            return Response({
                'status': 'error',
                'errors': serializer.errors,
                'message': 'Validation failed. Please check the errors.',
                'received_data': request.data
            }, status=status.HTTP_400_BAD_REQUEST)
            
        expense = serializer.save()
        print(f"Expense created successfully. ID: {expense.id}")
        
        # Track user action
        track_user_action(
            user=request.user,
            action='create',
            model_name='Expense',
            object_id=expense.id,
            description=f"Accountant {request.user.email} created expense record: {expense.reason}, amount: {expense.amount}"
        )
        
        response_serializer = ExpenseSerializer(expense)
        return Response({
            'status': 'success',
            'data': response_serializer.data,
            'message': 'Expense created successfully.'
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response(
            {'status': 'error', 'message': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )



def get_period_summary(period):
    today = timezone.now().date()
    
    if period == 'daily':
        start_date = today
        end_date = today + timedelta(days=1)
        period_name = 'Today'
    elif period == 'weekly':
        start_date = today - timedelta(days=today.weekday())
        end_date = start_date + timedelta(days=7)
        period_name = 'This Week'
    elif period == 'monthly':
        start_date = today.replace(day=1)
        next_month = today.replace(day=28) + timedelta(days=4)
        end_date = next_month - timedelta(days=next_month.day - 1)
        period_name = 'This Month'
    elif period == 'yearly':
        start_date = today.replace(month=1, day=1)
        end_date = today.replace(month=12, day=31)
        period_name = 'This Year'
    else:
        return None
    
    # Get income and expenses for the period
    income_data = Income.objects.filter(
        date__gte=start_date,
        date__lt=end_date
    ).aggregate(total=Sum('amount'))
    
    expense_data = Expense.objects.filter(
        date__gte=start_date,
        date__lt=end_date
    ).aggregate(total=Sum('amount'))
    
    total_income = income_data['total'] or 0
    total_expenses = expense_data['total'] or 0
    
    return {
        'period': period_name,
        'start_date': start_date,
        'end_date': end_date - timedelta(days=1),  # Adjust to be inclusive
        'total_income': float(total_income),
        'total_expenses': float(total_expenses),
        'net_balance': float(total_income - total_expenses)
    }


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def financial_summary(request):
    """
    Get financial summary for all time periods (daily, weekly, monthly, yearly)
    """
    try:
        # Track user action
        track_user_action(
            user=request.user,
            action='read',
            model_name='FinancialSummary',
            description=f"Accountant {request.user.email} viewed financial summary report"
        )
        
        # Get data for all periods
        periods = ['daily', 'weekly', 'monthly', 'yearly']
        data = {period: get_period_summary(period) for period in periods}
        
        # Calculate grand totals
        grand_totals = {
            'total_income': sum(period_data['total_income'] for period_data in data.values()),
            'total_expenses': sum(period_data['total_expenses'] for period_data in data.values()),
            'net_balance': sum(period_data['net_balance'] for period_data in data.values())
        }
        
        # Add grand totals to response
        response_data = {
            'periods': data,
            'grand_totals': grand_totals
        }
        
        serializer = FinancialSummarySerializer(data=data)
        if serializer.is_valid():
            return Response({
                'status': 'success',
                'data': {
                    'periods': serializer.data,
                    'grand_totals': grand_totals
                }
            })
        else:
            return Response({
                'status': 'error',
                'message': 'Invalid data',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        return Response(
            {'status': 'error', 'message': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def create_room(request):
    """
    Create a new room
    """
    try:
        # Only allow staff members to create rooms
        if not request.user.is_staff:
            return Response(
                {'status': 'error', 'message': 'You do not have permission to create rooms'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get data from request
        name = request.data.get('name')
        description = request.data.get('description', '')
        bed_count = request.data.get('bed_count')
        ward_id = request.data.get('ward')
        
        # Validate required fields
        if not name:
            return Response(
                {'status': 'error', 'message': 'Room name is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not bed_count:
            return Response(
                {'status': 'error', 'message': 'Bed count is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not ward_id:
            return Response(
                {'status': 'error', 'message': 'Ward ID is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate bed count is a positive integer
        try:
            bed_count = int(bed_count)
            if bed_count <= 0:
                raise ValueError()
        except (ValueError, TypeError):
            return Response(
                {'status': 'error', 'message': 'Bed count must be a positive integer'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if ward exists
        if not Ward.objects.filter(id=ward_id).exists():
            return Response(
                {'status': 'error', 'message': 'Ward not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if room with this name already exists in the same ward
        if Room.objects.filter(name__iexact=name, ward_id=ward_id).exists():
            return Response(
                {'status': 'error', 'message': 'A room with this name already exists in this ward'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create the room
        room = Room.objects.create(
            name=name,
            description=description,
            bed_count=bed_count,
            ward_id=ward_id
        )
        
        # Track user action
        track_user_action(
            user=request.user,
            action='create',
            model_name='Room',
            object_id=room.id,
            description=f"Admin {request.user.email} created room '{room.name}' with {bed_count} beds in ward {room.ward.name}"
        )
        
        return Response(
            {
                'status': 'success',
                'message': 'Room created successfully',
                'data': {
                    'id': room.id,
                    'name': room.name,
                    'description': room.description,
                    'bed_count': room.bed_count,
                    'ward': room.ward.id,
                    'ward_name': room.ward.name
                }
            },
            status=status.HTTP_201_CREATED
        )
        
    except Exception as e:
        return Response(
            {'status': 'error', 'message': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )









"""
ADMIN VIEW
"""

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def non_superuser_list(request):
    """
    Get a list of all non-superuser users
    """
    try:
        # Track user action
        track_user_action(
            user=request.user,
            action='read',
            model_name='User',
            description=f"Admin {request.user.email} viewed list of non-superuser users"
        )
        
        # Get all non-superuser users
        users = APPLICATIONS_USER_MODEL.objects.filter(is_superuser=False).order_by('first_name', 'last_name')
        
        # Serialize the data
        serializer = NonSuperuserUserSerializer(users, many=True)
        
        return Response({
            'status': 'success',
            'count': len(serializer.data),
            'data': serializer.data
        })
        
    except Exception as e:
        return Response(
            {'status': 'error', 'message': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )



@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def user_profile_detail(request, user_id):
    """
    Get detailed profile information for a specific user
    """
    try:
        # Get the user by ID, excluding superusers
        user = APPLICATIONS_USER_MODEL.objects.get(
            id=user_id,
            is_superuser=False
        )
        
        # Track user action
        track_user_action(
            user=request.user,
            action='read',
            model_name='User',
            object_id=user.id,
            action_taken_on=user,
            description=f"Admin {request.user.email} viewed profile details for user {user.email}"
        )
        
        # Serialize the data
        serializer = UserProfileSerializer(user)
        
        return Response({
            'status': 'success',
            'data': serializer.data
        })
        
    except APPLICATIONS_USER_MODEL.DoesNotExist:
        return Response(
            {'status': 'error', 'message': 'User not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'status': 'error', 'message': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )




@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def list_roles(request):
    """
    Get a list of all available roles
    """
    try:
        # Only allow staff members to view roles
        if not request.user.is_staff:
            return Response(
                {'status': 'error', 'message': 'You do not have permission to view roles'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Track user action
        track_user_action(
            user=request.user,
            action='read',
            model_name='Role',
            description=f"Admin {request.user.email} viewed list of available roles"
        )
        
        # Get all groups and serialize them
        roles = Group.objects.all().values('id', 'name').order_by('name')
        
        return Response({
            'status': 'success',
            'count': len(roles),
            'data': list(roles)
        })
        
    except Exception as e:
        return Response(
            {'status': 'error', 'message': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )







@api_view(['PATCH'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def update_user_role(request, user_id):
    """
    Update a user's role
    """
    try:
        # Get the user to update (exclude superusers)
        user = APPLICATIONS_USER_MODEL.objects.get(
            id=user_id,
            is_superuser=False
        )
        
        # Only allow admins to update roles
        if not request.user.is_staff:
            return Response(
                {'status': 'error', 'message': 'You do not have permission to update roles'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = UserRoleUpdateSerializer(
            user,
            data=request.data,
            partial=True,
            context={'request': request}
        )
        
        if serializer.is_valid():
            updated_user = serializer.save()
            
            # Track user action
            track_user_action(
                user=request.user,
                action='update',
                model_name='User',
                object_id=user.id,
                action_taken_on=user,
                description=f"Admin {request.user.email} updated role for user {user.email} to {user.role.name if user.role else 'None'}"
            )
            
            # Return the updated user data
            user_serializer = UserProfileSerializer(updated_user, context={'request': request})
            return Response({
                'status': 'success',
                'message': 'User role updated successfully',
                'data': user_serializer.data
            })
        
        return Response({
            'status': 'error',
            'message': 'Validation error',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
        
    except APPLICATIONS_USER_MODEL.DoesNotExist:
        return Response(
            {'status': 'error', 'message': 'User not found or is a superuser'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'status': 'error', 'message': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )






@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def list_appointments(request):
    """
    Get a list of all appointments
    """
    try:
        # Only allow staff members to view all appointments
        if not request.user.is_staff:
            return Response(
                {'status': 'error', 'message': 'You do not have permission to view appointments'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Track user action
        track_user_action(
            user=request.user,
            action='read',
            model_name='Appointment',
            description=f"Admin {request.user.email} viewed list of all appointments"
        )
        
        # Get all appointments ordered by date and time
        appointments = Appointment.objects.select_related('patient', 'doctor').order_by('-appointment_date')
        
        # Serialize the data
        serializer = AppointmentSerializer(appointments, many=True)
        
        return Response({
            'status': 'success',
            'count': len(serializer.data),
            'data': serializer.data
        })
        
    except Exception as e:
        return Response(
            {'status': 'error', 'message': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )




@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def statistics_summary(request):
    """
    Get hospital statistics including:
    - Number of patient users
    - Number of nurse users  
    - Number of doctor users
    - Total number of beds
    - Number of occupied beds
    """
    try:
        # Only allow staff members to view statistics
        if not request.user.is_staff:
            return Response(
                {'status': 'error', 'message': 'You do not have permission to view statistics'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Track user action
        track_user_action(
            user=request.user,
            action='read',
            model_name='Statistics',
            description=f"Admin {request.user.email} viewed hospital statistics summary"
        )
        
        # Count users by role
        patient_count = APPLICATIONS_USER_MODEL.objects.filter(role__name='patient', is_active=True).count()
        nurse_count = APPLICATIONS_USER_MODEL.objects.filter(role__name='nurse', is_active=True).count()
        doctor_count = APPLICATIONS_USER_MODEL.objects.filter(role__name='doctor', is_active=True).count()
        
        # Count beds
        total_beds = Bed.objects.count()
        occupied_beds = Bed.objects.filter(is_occupied=True).count()
        
        statistics_data = {
            'users': {
                'patients': patient_count,
                'nurses': nurse_count,
                'doctors': doctor_count
            },
            'beds': {
                'total': total_beds,
                'occupied': occupied_beds,
                'available': total_beds - occupied_beds
            }
        }
        
        return Response({
            'status': 'success',
            'data': statistics_data,
            'message': 'Statistics retrieved successfully.'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'status': 'error', 'message': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )




@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def admission_discharge_statistics(request):
    """
    Get admission and discharge statistics for week, month, and year arrays
    Returns arrays of admitted and discharged patient counts grouped by time periods
    """
    try:
        # Only allow staff members to view statistics
        if not request.user.is_staff:
            return Response(
                {'status': 'error', 'message': 'You do not have permission to view statistics'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Track user action
        track_user_action(
            user=request.user,
            action='read',
            model_name='Statistics',
            description=f"Admin {request.user.email} viewed admission/discharge statistics"
        )
        
        # Get current date
        now = timezone.now()
        
        # Weekly statistics (last 12 weeks)
        weekly_admissions = (
            Admission.objects
            .filter(admission_date__gte=now - timedelta(weeks=12))
            .annotate(period=TruncWeek('admission_date'))
            .values('period')
            .annotate(admitted=Count('id'))
            .order_by('period')
        )
        
        weekly_discharges = (
            Admission.objects
            .filter(
                discharge_date__isnull=False,
                discharge_date__gte=now - timedelta(weeks=12)
            )
            .annotate(period=TruncWeek('discharge_date'))
            .values('period')
            .annotate(discharged=Count('id'))
            .order_by('period')
        )
        
        # Monthly statistics (last 12 months)
        monthly_admissions = (
            Admission.objects
            .filter(admission_date__gte=now - timedelta(days=365))
            .annotate(period=TruncMonth('admission_date'))
            .values('period')
            .annotate(admitted=Count('id'))
            .order_by('period')
        )
        
        monthly_discharges = (
            Admission.objects
            .filter(
                discharge_date__isnull=False,
                discharge_date__gte=now - timedelta(days=365)
            )
            .annotate(period=TruncMonth('discharge_date'))
            .values('period')
            .annotate(discharged=Count('id'))
            .order_by('period')
        )
        
        # Yearly statistics (last 5 years)
        yearly_admissions = (
            Admission.objects
            .filter(admission_date__gte=now - timedelta(days=1825))
            .annotate(period=TruncYear('admission_date'))
            .values('period')
            .annotate(admitted=Count('id'))
            .order_by('period')
        )
        
        yearly_discharges = (
            Admission.objects
            .filter(
                discharge_date__isnull=False,
                discharge_date__gte=now - timedelta(days=1825)
            )
            .annotate(period=TruncYear('discharge_date'))
            .values('period')
            .annotate(discharged=Count('id'))
            .order_by('period')
        )
        
        # Convert to arrays format
        def merge_admission_discharge(admissions, discharges):
            # Create a dictionary for quick lookup
            discharge_dict = {d['period']: d['discharged'] for d in discharges}
            
            result = []
            for admission in admissions:
                period = admission['period']
                result.append({
                    'period': period,
                    'admitted': admission['admitted'],
                    'discharged': discharge_dict.get(period, 0)
                })
            
            # Add any discharge periods that don't have admissions
            admission_periods = {a['period'] for a in admissions}
            for discharge in discharges:
                if discharge['period'] not in admission_periods:
                    result.append({
                        'period': discharge['period'],
                        'admitted': 0,
                        'discharged': discharge['discharged']
                    })
            
            return sorted(result, key=lambda x: x['period'])
        
        statistics_data = {
            'weekly': merge_admission_discharge(weekly_admissions, weekly_discharges),
            'monthly': merge_admission_discharge(monthly_admissions, monthly_discharges),
            'yearly': merge_admission_discharge(yearly_admissions, yearly_discharges)
        }
        
        return Response({
            'status': 'success',
            'data': statistics_data,
            'message': 'Admission and discharge statistics retrieved successfully.'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'status': 'error', 'message': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )



@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def bed_occupancy_details(request):
    """
    Get detailed bed occupancy data including:
    - Total beds, occupied beds, available beds, occupancy percentage
    - All wards with their rooms and beds (even if wards have no rooms)
    - Each bed's occupancy status and patient details (first_name, last_name)
    """
    try:
        # Only allow staff members to view statistics
        if not request.user.is_staff:
            return Response(
                {'status': 'error', 'message': 'You do not have permission to view statistics'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Track user action
        track_user_action(
            user=request.user,
            action='read',
            model_name='BedOccupancy',
            description=f"Admin {request.user.email} viewed bed occupancy details"
        )
        
        # Get all beds with related data
        beds = Bed.objects.select_related('room__ward', 'patient').all()
        
        # Calculate overall statistics
        total_beds = beds.count()
        occupied_beds = beds.filter(is_occupied=True).count()
        available_beds = total_beds - occupied_beds
        occupancy_percentage = round((occupied_beds / total_beds * 100), 1) if total_beds > 0 else 0
        
        # Get all wards first
        all_wards = Ward.objects.all().order_by('name')
        
        # Get all rooms with their wards
        all_rooms = Room.objects.select_related('ward').all().order_by('name')
        
        # Debug: Log what we found
        print(f"DEBUG: Found {all_wards.count()} wards")
        print(f"DEBUG: Found {all_rooms.count()} rooms")
        print(f"DEBUG: Found {beds.count()} beds")
        
        # Initialize wards dict with all wards and their rooms
        wards_dict = {}
        for ward in all_wards:
            wards_dict[ward.name] = {
                'name': ward.name,
                'rooms': {}
            }
            print(f"DEBUG: Added ward: {ward.name}")
        
        # Add all rooms to their respective wards (even if no beds)
        for room in all_rooms:
            ward_name = room.ward.name
            if ward_name in wards_dict:
                wards_dict[ward_name]['rooms'][room.name] = {
                    'name': room.name,
                    'beds': []
                }
                print(f"DEBUG: Added room '{room.name}' to ward '{ward_name}'")
            else:
                print(f"DEBUG: Room '{room.name}' has ward '{ward_name}' but ward not found in wards_dict")
        
        # Create a mapping of existing beds by room and bed_id
        existing_beds = {}
        for bed in beds:
            if bed.room and bed.room.ward:
                ward_name = bed.room.ward.name
                room_name = bed.room.name
                
                if ward_name not in existing_beds:
                    existing_beds[ward_name] = {}
                if room_name not in existing_beds[ward_name]:
                    existing_beds[ward_name][room_name] = {}
                
                # Get patient details if bed is occupied
                patient_name = None
                if bed.is_occupied and bed.patient:
                    patient_name = f"{bed.patient.first_name} {bed.patient.last_name}".strip()
                
                existing_beds[ward_name][room_name][bed.id] = {
                    'occupied': bed.is_occupied,
                    'patient': patient_name,
                    'bed_id': bed.id
                }
                print(f"DEBUG: Found existing bed {bed.id} in room '{room_name}' in ward '{ward_name}' (occupied: {bed.is_occupied})")
        
        # Generate all beds based on room bed_count
        for ward_name in wards_dict:
            for room_name in wards_dict[ward_name]['rooms']:
                # Find the room object to get bed_count
                room_obj = next((room for room in all_rooms if room.name == room_name and room.ward.name == ward_name), None)
                
                if room_obj:
                    bed_count = room_obj.bed_count
                    print(f"DEBUG: Room '{room_name}' in ward '{ward_name}' has bed_count: {bed_count}")
                    
                    # Get existing beds for this room
                    room_existing_beds = existing_beds.get(ward_name, {}).get(room_name, {})
                    
                    # Generate beds from 1 to bed_count
                    for bed_num in range(1, bed_count + 1):
                        # Check if this bed exists and is occupied
                        bed_info = None
                        for existing_bed_id, existing_data in room_existing_beds.items():
                            if existing_bed_id == bed_num:
                                bed_info = existing_data
                                break
                        
                        if bed_info:
                            # Use existing bed data
                            wards_dict[ward_name]['rooms'][room_name]['beds'].append({
                                'label': f'Bed {bed_num}',
                                'occupied': bed_info['occupied'],
                                'patient': bed_info['patient'],
                                'bed_id': bed_info['bed_id']
                            })
                            print(f"DEBUG: Added existing bed {bed_num} to room '{room_name}' in ward '{ward_name}' (occupied: {bed_info['occupied']})")
                        else:
                            # Create empty bed entry
                            wards_dict[ward_name]['rooms'][room_name]['beds'].append({
                                'label': f'Bed {bed_num}',
                                'occupied': False,
                                'patient': None,
                                'bed_id': bed_num
                            })
                            print(f"DEBUG: Added empty bed {bed_num} to room '{room_name}' in ward '{ward_name}'")
        
        # Convert rooms dict to list and sort
        wards_list = []
        for ward_data in wards_dict.values():
            rooms_list = []
            for room_data in ward_data['rooms'].values():
                # Sort beds by bed_id
                room_data['beds'].sort(key=lambda x: x['bed_id'])
                rooms_list.append(room_data)
            
            # Sort rooms by name
            rooms_list.sort(key=lambda x: x['name'])
            
            wards_list.append({
                'name': ward_data['name'],
                'rooms': rooms_list
            })
        
        # Sort wards by name
        wards_list.sort(key=lambda x: x['name'])
        
        response_data = {
            'summary': {
                'total_beds': total_beds,
                'occupied_beds': occupied_beds,
                'available_beds': available_beds,
                'occupancy_percentage': occupancy_percentage
            },
            'wards': wards_list
        }
        
        return Response({
            'status': 'success',
            'data': response_data,
            'message': 'Bed occupancy details retrieved successfully.'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'status': 'error', 'message': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )





@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_all_wards(request):
    """
    Get all wards in the hospital with room and bed counts
    """
    try:
        # Only allow staff members to view wards
        if not request.user.is_staff:
            return Response(
                {'status': 'error', 'message': 'You do not have permission to view wards'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Track user action
        track_user_action(
            user=request.user,
            action='read',
            model_name='Ward',
            description=f"Admin {request.user.email} viewed list of all wards"
        )
        
        # Get all wards
        wards = Ward.objects.all().order_by('name')
        
        # Serialize wards with room and bed counts
        serializer = WardSerializer(wards, many=True)
        
        return Response({
            'status': 'success',
            'data': serializer.data,
            'message': 'Wards retrieved successfully.'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'status': 'error', 'message': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )



@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def create_ward(request):
    """
    Create a new ward
    """
    try:
        # Only allow staff members to create wards
        if not request.user.is_staff:
            return Response(
                {'status': 'error', 'message': 'You do not have permission to create wards'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get data from request
        name = request.data.get('name')
        description = request.data.get('description', '')
        
        # Validate required fields
        if not name:
            return Response(
                {'status': 'error', 'message': 'Ward name is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if ward with this name already exists
        if Ward.objects.filter(name__iexact=name).exists():
            return Response(
                {'status': 'error', 'message': 'A ward with this name already exists'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create the ward
        ward = Ward.objects.create(
            name=name,
            description=description
        )
        
        # Track user action
        track_user_action(
            user=request.user,
            action='create',
            model_name='Ward',
            object_id=ward.id,
            description=f"Admin {request.user.email} created ward '{ward.name}'"
        )
        
        return Response(
            {
                'status': 'success',
                'message': 'Ward created successfully',
                'data': {
                    'id': ward.id,
                    'name': ward.name,
                    'description': ward.description
                }
            },
            status=status.HTTP_201_CREATED
        )
        
    except Exception as e:
        return Response(
            {'status': 'error', 'message': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )



@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_all_wards(request):
    """
    Get all wards in the hospital with room and bed counts
    """
    try:
        # Only allow staff members to view wards
        if not request.user.is_staff:
            return Response(
                {'status': 'error', 'message': 'You do not have permission to view wards'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Track user action
        track_user_action(
            user=request.user,
            action='read',
            model_name='Ward',
            description=f"Admin {request.user.email} viewed list of all wards"
        )
        
        # Get all wards
        wards = Ward.objects.all().order_by('name')
        
        # Serialize wards with room and bed counts
        serializer = WardSerializer(wards, many=True)
        
        return Response({
            'status': 'success',
            'data': serializer.data,
            'message': 'Wards retrieved successfully.'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'status': 'error', 'message': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )




@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def create_drug(request):
    """
    Create a new drug
    """
    try:
        # Only allow staff members to create drugs
        if not request.user.is_staff:
            return Response(
                {'status': 'error', 'message': 'You do not have permission to create drugs'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = DrugSerializer(data=request.data)
        if serializer.is_valid():
            drug = serializer.save()
            
            # Track user action
            track_user_action(
                user=request.user,
                action='create',
                model_name='Drug',
                object_id=drug.id,
                description=f"Admin {request.user.email} created drug '{drug.name}'"
            )
            
            return Response({
                'status': 'success',
                'data': DrugSerializer(drug).data,
                'message': 'Drug created successfully.'
            }, status=status.HTTP_201_CREATED)
        else:
            return Response({
                'status': 'error',
                'message': 'Invalid data provided.',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        return Response(
            {'status': 'error', 'message': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )




@api_view(['PUT'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def update_drug(request, drug_id):
    """
    Update an existing drug
    """
    try:
        # Only allow staff members to update drugs
        if not request.user.is_staff:
            return Response(
                {'status': 'error', 'message': 'You do not have permission to update drugs'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            drug = Drug.objects.get(id=drug_id)
        except Drug.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Drug not found.'
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = DrugSerializer(drug, data=request.data, partial=True)
        print(f"DEBUG: Update drug request data: {request.data}")
        print(f"DEBUG: Drug before update: {drug}")
        if serializer.is_valid():
            updated_drug = serializer.save()
            
            # Track user action
            track_user_action(
                user=request.user,
                action='update',
                model_name='Drug',
                object_id=drug.id,
                description=f"Admin {request.user.email} updated drug '{updated_drug.name}'"
            )
            
            return Response({
                'status': 'success',
                'data': DrugSerializer(updated_drug).data,
                'message': 'Drug updated successfully.'
            }, status=status.HTTP_200_OK)
        else:
            print(f"DEBUG: Serializer errors: {serializer.errors}")
            return Response({
                'status': 'error',
                'message': 'Invalid data provided.',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        return Response(
            {'status': 'error', 'message': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )





@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_all_activities(request):
    """
    Get all activities
    """
    try:
        activities = Activity.objects.all().order_by('-timestamp')
        serializer = ActivitySerializer(activities, many=True)
        
        return Response({
            'status': 'success',
            'count': len(serializer.data),
            'activities': serializer.data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'status': 'error', 'message': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
