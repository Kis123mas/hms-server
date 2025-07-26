# import from django rest_framework
from django.contrib.auth import authenticate
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from knox.auth import TokenAuthentication
from django.contrib.auth import logout

# external package import
from knox.models import AuthToken
from knox.views import LogoutView as KnoxLogoutView
from django.utils import timezone
from django.contrib.auth.models import Group

from rest_framework.permissions import IsAuthenticated

# local import
from .serializers import RegisterSerializer


"""
This file handles the view for user authentication and authorization. 
Below are views that handles user registration, login and user logout. 
Here knox is used to generate tokens for users.
"""

# view to register user
@api_view(['POST'])
def register_api(request):
    """
    Register function with modified response
    """
    serializer = RegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    user = serializer.save()

    return Response({
        'status': 'success',
        'code': status.HTTP_201_CREATED,
        'message': 'User Created successfully',
        'user_data': {
            'id': user.id,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'role': {'id': user.role.id, 'name': user.role.name} if user.role else None
        },
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
def login_api(request):
    """
    Login function with modified response.
    """
    email = request.data.get('email')
    password = request.data.get('password')

    user = authenticate(request, email=email, password=password)

    if user is not None:
        # Update last login time
        user.last_login = timezone.now()
        user.save()

        # Delete existing tokens for the user
        AuthToken.objects.filter(user=user).delete()

        # Create a new token
        _, token = AuthToken.objects.create(user)

        return Response({
            'status': 'success',
            'code': status.HTTP_200_OK,
            'message': 'Access Granted',
            'user_info': {
                'id': user.id,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email,
                'is_staff': user.is_staff,
                'is_superuser': user.is_superuser,
                'role': {'id': user.role.id, 'name': user.role.name} if user.role else None,
            },
            'token': token
        })
    else:
        return Response({
            'status': 'error',
            'code': status.HTTP_401_UNAUTHORIZED,
            'message': 'Invalid credentials'
        }, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def logout_user(request):
    """
    Custom logout function with token deletion using Knox
    """
    if request.method == 'POST':
        # Delete all tokens associated with the user
        AuthToken.objects.filter(user=request.user).delete()

        # Perform the actual logout
        logout(request)

        # Return a success response
        return Response({
            'status': 'success',
            'code': status.HTTP_200_OK,
            'message': 'Successfully logged out.'
        })

    return Response({
        'status': 'error',
        'code': status.HTTP_405_METHOD_NOT_ALLOWED,
        'message': 'Method not allowed'
    }, status=status.HTTP_405_METHOD_NOT_ALLOWED)