from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import Group
from knox.auth import TokenAuthentication
from utils import APPLICATIONS_USER_MODEL
from .serializers import PatientUserSerializer

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