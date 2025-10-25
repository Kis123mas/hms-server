# import from django rest_framework
from django.contrib.auth import authenticate
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from knox.auth import TokenAuthentication
from django.contrib.auth import logout
from healthManagement.models import VerificationCode
import random


# external package import
from knox.models import AuthToken
from knox.views import LogoutView as KnoxLogoutView
from django.utils import timezone
from django.contrib.auth.models import Group

from rest_framework.permissions import IsAuthenticated
from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests

# local import
from .serializers import (
    RegisterSerializer,
    ForgotPasswordSerializer,
    ResetPasswordSerializer,
    GoogleAuthSerializer,
)
from .models import CustomUser
from datetime import timedelta


"""
This file handles the view for user authentication and authorization. 
Below are views that handles user registration, login and user logout. 
Here knox is used to generate tokens for users.
"""

# view to register user
@api_view(['POST'])
def register_api(request):
    """
    Register function with verification email
    """
    try:
        # Log incoming request data for debugging
        print("Registration request data:", request.data)
        
        serializer = RegisterSerializer(data=request.data)
        
        # Manually validate to get detailed errors
        if not serializer.is_valid():
            print("Validation errors:", serializer.errors)
            return Response(
                {
                    'status': 'error',
                    'code': status.HTTP_400_BAD_REQUEST,
                    'message': 'Validation error',
                    'errors': serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = serializer.save()

            # Generate a 6-digit random verification code
            code = f"{random.randint(0, 999999):06d}"

            # Store it in the database for later verification
            VerificationCode.objects.create(user=user, code=code)

            from django.core.mail import send_mail
            try:
                # Send email
                subject = "Verify your account"
                message = f"Hello {user.first_name},\n\nYour verification code is: {code}\n\nEnter this code in the app to activate your account and This code will expire in 60 seconds"
                send_mail(
                    subject,
                    message,
                    None,  # will use DEFAULT_FROM_EMAIL
                    [user.email],
                    fail_silently=True,  # Changed to True to prevent crashing
                )
            except Exception as e:
                # Log the error but don't block the registration process
                print(f"[EMAIL ERROR] Could not send verification email: {e}")

            return Response({
                'status': 'success',
                'code': status.HTTP_201_CREATED,
                'message': 'User created successfully. A verification code has been sent to your email.',
                'user_data': {
                    'id': user.id,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'email': user.email,
                    'role': {'id': user.role.id, 'name': user.role.name} if user.role else None
                },
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            print(f"[REGISTRATION ERROR] {str(e)}")
            return Response(
                {
                    'status': 'error',
                    'code': status.HTTP_500_INTERNAL_SERVER_ERROR,
                    'message': 'An error occurred during registration',
                    'error': str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    except Exception as e:
        print(f"[REGISTRATION ERROR] {str(e)}")
        return Response(
            {
                'status': 'error',
                'code': status.HTTP_500_INTERNAL_SERVER_ERROR,
                'message': 'An error occurred during registration',
                'error': str(e)
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


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


@api_view(['POST'])
def regenerate_code_api(request):
    email = request.data.get('email')
    if not email:
        return Response({
            'status': 'error',
            'message': 'Email is required.'
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = CustomUser.objects.get(email=email)
    except CustomUser.DoesNotExist:
        return Response({
            'status': 'error',
            'message': 'User with this email does not exist.'
        }, status=status.HTTP_404_NOT_FOUND)

    if user.is_active:
        return Response({
            'status': 'error',
            'message': 'This account is already active.'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Delete old code and create a new one
    VerificationCode.objects.filter(user=user).delete()
    code = f"{random.randint(100000, 999999)}"
    VerificationCode.objects.create(user=user, code=code)

    # Send email
    from django.core.mail import send_mail
    try:
        subject = "New Verification Code"
        message = f"Hello {user.first_name},\n\nYour new verification code is: {code}\n\nThis code will expire in 60 seconds."
        send_mail(
            subject,
            message,
            None,
            [user.email],
            fail_silently=False,
        )
    except Exception as e:
        print(f"[EMAIL ERROR] Could not send new verification email: {e}")
        return Response({
            'status': 'error',
            'message': 'Failed to send verification email. Please try again later.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response({
        'status': 'success',
        'message': 'A new verification code has been sent to your email.'
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
def verify_code_api(request):
    email = request.data.get('email')
    code = request.data.get('code')

    if not email or not code:
        return Response({
            'status': 'error',
            'message': 'Email and code are required.'
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = CustomUser.objects.get(email=email)
        verification_code = VerificationCode.objects.get(user=user, code=code)

        # Check if code is expired (60 seconds)
        if timezone.now() > verification_code.created_at + timedelta(seconds=60):
            return Response({
                'status': 'error',
                'message': 'Verification code has expired. Please request a new one.'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Activate user
        user.is_active = True
        user.save()

        # Delete the verification code after use
        verification_code.delete()

        return Response({
            'status': 'success',
            'message': 'Account activated successfully.'
        }, status=status.HTTP_200_OK)

    except (CustomUser.DoesNotExist, VerificationCode.DoesNotExist):
        return Response({
            'status': 'error',
            'message': 'Invalid email or verification code.'
        })


# Forgot password: request a reset code
@api_view(['POST'])
def forgot_password_api(request):
    serializer = ForgotPasswordSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    email = serializer.validated_data['email']

    try:
        user = CustomUser.objects.get(email=email)
    except CustomUser.DoesNotExist:
        # Do not reveal account existence
        return Response({
            'status': 'success',
            'message': 'If the email exists, a reset code has been sent.'
        }, status=status.HTTP_200_OK)

    # Delete old codes and create a new one
    VerificationCode.objects.filter(user=user).delete()
    code = f"{random.randint(100000, 999999)}"
    VerificationCode.objects.create(user=user, code=code)

    # Send email (console backend in dev)
    from django.core.mail import send_mail
    try:
        subject = "Password Reset Code"
        message = (
            f"Hello {user.first_name or 'User'},\n\n"
            f"Your password reset code is: {code}\n\n"
            f"This code will expire in 60 seconds."
        )
        send_mail(subject, message, None, [user.email], fail_silently=True)
    except Exception as e:
        print(f"[EMAIL ERROR] Could not send reset email: {e}")

    return Response({
        'status': 'success',
        'message': 'If the email exists, a reset code has been sent.'
    }, status=status.HTTP_200_OK)


# Reset password with code
@api_view(['POST'])
def reset_password_api(request):
    serializer = ResetPasswordSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    email = serializer.validated_data['email']
    code = serializer.validated_data['code']
    new_password = serializer.validated_data['new_password']

    try:
        user = CustomUser.objects.get(email=email)
        verification_code = VerificationCode.objects.get(user=user, code=code)
    except (CustomUser.DoesNotExist, VerificationCode.DoesNotExist):
        return Response({
            'status': 'error',
            'message': 'Invalid email or verification code.'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Expiry check (60 seconds)
    if timezone.now() > verification_code.created_at + timedelta(seconds=60):
        return Response({
            'status': 'error',
            'message': 'Verification code has expired. Please request a new one.'
        }, status=status.HTTP_400_BAD_REQUEST)

    user.set_password(new_password)
    user.save()

    verification_code.delete()

    return Response({
        'status': 'success',
        'message': 'Password has been reset successfully.'
    }, status=status.HTTP_200_OK)


# Google Sign-In (login/register with Gmail)
@api_view(['POST'])
def google_login_api(request):
    """
    Accepts a Google ID token from the frontend, verifies it, and then
    logs in or creates the user, returning a Knox token and user info.
    Request body: { id_token: string }
    """
    serializer = GoogleAuthSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    token = serializer.validated_data['id_token']

    try:
        # Verify the token with Google
        idinfo = google_id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            audience=None,  # Accept any client; optionally restrict to your CLIENT_ID
        )

        # Extract profile info
        email = idinfo.get('email')
        first_name = idinfo.get('given_name') or ''
        last_name = idinfo.get('family_name') or ''
        email_verified = idinfo.get('email_verified', False)

        if not email:
            return Response({
                'status': 'error',
                'message': 'Unable to retrieve email from Google token.'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Find or create user
        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            # Assign default role if exists
            try:
                default_role = Group.objects.get(name='patient')
            except Group.DoesNotExist:
                default_role = None

            user = CustomUser.objects.create(
                email=email,
                first_name=first_name,
                last_name=last_name,
                role=default_role,
                is_active=True,  # activate immediately since Google verified
            )
            user.set_unusable_password()
            user.save()

        # If the account was previously inactive, activate when Google verifies email
        if not user.is_active and email_verified:
            user.is_active = True
            user.save()

        # Issue Knox token
        AuthToken.objects.filter(user=user).delete()
        _, token_value = AuthToken.objects.create(user)

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
            'token': token_value,
        }, status=status.HTTP_200_OK)

    except ValueError:
        return Response({
            'status': 'error',
            'message': 'Invalid Google ID token.'
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def change_password(request):
    """
    Change user password
    Requires: current_password, new_password, confirm_password
    """
    user = request.user
    
    # Get passwords from request
    current_password = request.data.get('current_password')
    new_password = request.data.get('new_password')
    confirm_password = request.data.get('confirm_password')
    
    # Validate required fields
    if not current_password or not new_password or not confirm_password:
        return Response({
            'status': 'error',
            'message': 'All fields are required (current_password, new_password, confirm_password)'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if current password is correct
    if not user.check_password(current_password):
        return Response({
            'status': 'error',
            'message': 'Current password is incorrect'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if new passwords match
    if new_password != confirm_password:
        return Response({
            'status': 'error',
            'message': 'New password and confirm password do not match'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Validate new password length
    if len(new_password) < 8:
        return Response({
            'status': 'error',
            'message': 'New password must be at least 8 characters long'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if new password is same as current password
    if current_password == new_password:
        return Response({
            'status': 'error',
            'message': 'New password must be different from current password'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Set new password
    user.set_password(new_password)
    user.save()
    
    return Response({
        'status': 'success',
        'message': 'Password changed successfully'
    }, status=status.HTTP_200_OK)





