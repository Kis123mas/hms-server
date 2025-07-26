from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import *

APPLICATIONS_USER_MODEL = get_user_model()






class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['phone_number', 'address', 'date_of_birth', 'profile_picture']
        extra_kwargs = {
            'profile_picture': {'required': False}
        }


class UserProfileSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(source='user_profile', read_only=True)
    role = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = APPLICATIONS_USER_MODEL
        fields = [
            'id',
            'email',
            'full_name',
            'first_name',
            'last_name',
            'role',
            'is_active',
            'date_joined',
            'profile'  # Nested profile information
        ]
    
    def get_role(self, obj):
        return obj.role.name if obj.role else None
    
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"


        
class PatientUserSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()
    profile = ProfileSerializer(read_only=True)

    class Meta:
        model = APPLICATIONS_USER_MODEL
        fields = [
            'id', 
            'email', 
            'first_name', 
            'last_name', 
            'role',
            'profile'  # Include the nested profile
        ]
    
    def get_role(self, obj):
        return obj.role.name if obj.role else None



class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = APPLICATIONS_USER_MODEL
        fields = ['id', 'email', 'first_name', 'last_name']

class AppointmentSerializer(serializers.ModelSerializer):
    patient = UserSerializer(read_only=True)
    doctor = UserSerializer(read_only=True)
    doctor_id = serializers.PrimaryKeyRelatedField(
        queryset=APPLICATIONS_USER_MODEL.objects.filter(role__name='doctor'),
        write_only=True,
        source='doctor'
    )
    patient_id = serializers.PrimaryKeyRelatedField(
        queryset=APPLICATIONS_USER_MODEL.objects.filter(role__name='patient'),
        write_only=True,
        source='patient'
    )

    class Meta:
        model = Appointment
        fields = [
            'id', 'patient', 'doctor', 'appointment_date', 
            'reason', 'status', 'created_at', 'updated_at',
            'doctor_id', 'patient_id'
        ]
        read_only_fields = ['status', 'created_at', 'updated_at']

    def validate_appointment_date(self, value):
        if value < timezone.now():
            raise serializers.ValidationError("Appointment date cannot be in the past")
        return value



class DoctorAppointmentSerializer(serializers.ModelSerializer):
    patient_name = serializers.SerializerMethodField()
    patient_email = serializers.CharField(source='patient.email')
    formatted_date = serializers.SerializerMethodField()

    class Meta:
        model = Appointment
        fields = [
            'id',
            'patient_name',
            'patient_email',
            'appointment_date',
            'formatted_date',
            'reason',
            'status'
        ]

    def get_patient_name(self, obj):
        return f"{obj.patient.first_name} {obj.patient.last_name}"

    def get_formatted_date(self, obj):
        return obj.appointment_date.strftime('%d-%m-%Y %H:%M')