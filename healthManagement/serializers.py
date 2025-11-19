from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils.dateparse import parse_datetime
from django.db.models import Q, Sum
from django.contrib.auth.models import Group
from django.db.models import Count, Q, Prefetch
from .models import *
from rest_framework.exceptions import ValidationError
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.db import transaction
from utils import APPLICATIONS_USER_MODEL
from .models import Treatment
from rest_framework import serializers
from django.contrib.auth import get_user_model

APPLICATIONS_USER_MODEL = get_user_model()


class ChatRequestSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=1000, required=True)
    conversation_history = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        allow_empty=True
    )


class ChatResponseSerializer(serializers.Serializer):
    response = serializers.CharField()
    conversation_id = serializers.CharField(required=False)


class TestTypesSerializer(serializers.ModelSerializer):
    """
    Serializer for TestTypes model
    """
    class Meta:
        model = TestTypes
        fields = ['id', 'name', 'description', 'price']


class PaymentMethodSerializer(serializers.ModelSerializer):
    """
    Serializer for PaymentMethod model
    """
    class Meta:
        model = PaymentMethod
        fields = ['id', 'name', 'account_number', 'bank', 'account_name']


class AdmissionSerializer(serializers.ModelSerializer):
    """
    Serializer for Admission model
    """
    patient_name = serializers.CharField(source='patient.get_full_name', read_only=True)
    admitted_by_name = serializers.CharField(source='admitted_by.get_full_name', read_only=True)
    bed_info = serializers.SerializerMethodField()
    admission_date_formatted = serializers.DateTimeField(source='admission_date', format='%Y-%m-%d %H:%M', read_only=True)
    
    class Meta:
        model = Admission
        fields = [
            'id', 'patient', 'patient_name', 'admitted_by', 'admitted_by_name',
            'bed', 'bed_info', 'admission_date', 'admission_date_formatted',
            'discharge_date', 'status'
        ]
        read_only_fields = ['admitted_by', 'admission_date', 'status']
    
    def get_bed_info(self, obj):
        if obj.bed:
            return {
                'id': obj.bed.id,
                'room': obj.bed.room.name,
                'ward': obj.bed.room.ward.name
            }
        return None
    
    def validate_bed(self, value):
        if value.is_occupied:
            raise serializers.ValidationError("This bed is already occupied")
        return value
    
    def validate_patient(self, value):
        if value.role.name != 'patient':
            raise serializers.ValidationError("The selected user is not a patient")
        
        # Check if patient is already admitted
        active_admission = Admission.objects.filter(
            patient=value,
            status='active'
        ).exists()
        
        if active_admission:
            raise serializers.ValidationError("This patient is already admitted")
        
        return value


class AdmitPatientSerializer(serializers.Serializer):
    bed_id = serializers.IntegerField()
    patient_id = serializers.IntegerField()
    
    def save(self, **kwargs):
        bed = Bed.objects.get(id=self.validated_data['bed_id'])
        patient = APPLICATIONS_USER_MODEL.objects.get(id=self.validated_data['patient_id'])
        
        # Update bed status
        bed.patient = patient
        bed.is_occupied = True
        bed.save()
        
        # Create or update admission record
        admission, created = Admission.objects.get_or_create(
            patient=patient,
            status='active',
            defaults={
                'admitted_by': self.context['request'].user,
                'bed': bed
            }
        )
        
        # If admission exists, update the bed
        if not created:
            admission.bed = bed
            admission.save()
        
        # Update patient's admission status in their profile
        if hasattr(patient, 'profile'):
            patient.profile.is_admitted = True
            patient.profile.save()
        
        return admission


class BedSpaceSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    patient_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Bed
        fields = ['id', 'is_occupied', 'status', 'patient_name']
    
    def get_status(self, obj):
        return 'Available' if not obj.is_occupied else 'Occupied'
    
    def get_patient_name(self, obj):
        if obj.is_occupied and obj.patient:
            return f"{obj.patient.first_name} {obj.patient.last_name}"
        return None

class RoomSpaceSerializer(serializers.ModelSerializer):
    beds = BedSpaceSerializer(many=True, read_only=True)
    available_beds = serializers.SerializerMethodField()
    unavailable_beds = serializers.SerializerMethodField()
    total_beds = serializers.IntegerField(source='bed_count', read_only=True)
    
    class Meta:
        model = Room
        fields = ['id', 'name', 'description', 'total_beds', 'available_beds', 'unavailable_beds', 'beds']
    
    def get_available_beds(self, obj):
        # Total beds that can exist in the room
        total_possible_beds = obj.bed_count
        # Currently occupied beds
        occupied_beds = self.get_unavailable_beds(obj)
        # Available beds are total possible minus occupied
        available = total_possible_beds - occupied_beds
        return max(0, available)  # Ensure we don't return negative numbers
    
    def get_unavailable_beds(self, obj):
        # Count of currently occupied beds
        return obj.beds.filter(is_occupied=True).count()

class WardSpaceSerializer(serializers.ModelSerializer):
    rooms = RoomSpaceSerializer(many=True, read_only=True)
    total_beds = serializers.SerializerMethodField()
    available_beds = serializers.SerializerMethodField()
    
    class Meta:
        model = Ward
        fields = ['id', 'name', 'description', 'total_beds', 'available_beds', 'rooms']
    
    def get_total_beds(self, obj):
        return sum(room.bed_count for room in obj.rooms.all())
    
    def get_available_beds(self, obj):
        total_available = 0
        for room in obj.rooms.all():
            # For each room, calculate available beds as (total beds - occupied beds)
            occupied = room.beds.filter(is_occupied=True).count()
            available = room.bed_count - occupied
            total_available += max(0, available)  # Add to ward total, ensure not negative
        return total_available



class MedicalRecordSerializer(serializers.ModelSerializer):
    """
    Serializer for creating and retrieving medical records
    """
    patient_id = serializers.IntegerField(write_only=True)
    appointment_id = serializers.IntegerField(required=False, allow_null=True)
    vital_signs_id = serializers.IntegerField(required=False, allow_null=True)
    doctor_info = serializers.SerializerMethodField()
    
    class Meta:
        model = MedicalRecord
        fields = [
            'id', 'patient_id', 'doctor', 'doctor_info', 'diagnosis', 'symptoms', 'notes',
            'status', 'date_created', 'last_updated', 'date_resolved',
            'appointment_id', 'is_treatment_created', 'vital_signs_id', 'is_test_result_ready',
            'requested_for_test'
        ]
        read_only_fields = ['doctor', 'date_created', 'last_updated', 'requested_for_test']
    
    def get_doctor_info(self, obj):
        """Get complete doctor information including profile"""
        doctor = obj.doctor
        if not doctor:
            return None
            
        profile = getattr(doctor, 'profile', None)
        
        doctor_data = {
            'id': doctor.id,
            'email': doctor.email,
            'first_name': doctor.first_name,
            'last_name': doctor.last_name,
            'full_name': f"{doctor.first_name} {doctor.last_name}",
            'specialization': None,
            'phone_number': None,
            'department': None
        }
        
        if profile:
            doctor_data.update({
                'specialization': getattr(profile, 'specialization', None),
                'phone_number': getattr(profile, 'phone_number', None),
                'department': profile.department.name if hasattr(profile, 'department') and profile.department else None
            })
            
            # Add profile picture URL if available
            if hasattr(profile, 'profile_picture') and profile.profile_picture:
                request = self.context.get('request')
                if request:
                    doctor_data['profile_picture'] = request.build_absolute_uri(profile.profile_picture.url)
                else:
                    doctor_data['profile_picture'] = profile.profile_picture.url
        
        return doctor_data
    
    def validate_patient_id(self, value):
        """Validate that the patient exists and is a patient"""
        try:
            patient = APPLICATIONS_USER_MODEL.objects.get(
                id=value,
                role__name='patient',
                is_active=True
            )
            return patient
        except APPLICATIONS_USER_MODEL.DoesNotExist:
            raise serializers.ValidationError("Patient not found or is not active.")
    
    def validate_appointment_id(self, value):
        """Validate that the appointment exists and is related to the patient"""
        if value is None:
            return None
            
        try:
            appointment = Appointment.objects.get(id=value)
            return appointment
        except Appointment.DoesNotExist:
            raise serializers.ValidationError("Appointment not found.")
    
    def validate_vital_signs_id(self, value):
        """Validate that the vital signs exist and are related to the patient"""
        if value is None:
            return None
            
        try:
            vital_signs = VitalSign.objects.get(id=value)
            return vital_signs
        except VitalSign.DoesNotExist:
            raise serializers.ValidationError("Vital signs record not found.")
    
    def create(self, validated_data):
        """Create a new medical record"""
        # Extract related objects
        patient = validated_data.pop('patient_id')
        appointment = validated_data.pop('appointment_id', None)
        vital_signs = validated_data.pop('vital_signs_id', None)
        
        # Get the doctor from the request
        doctor = self.context['request'].user
        
        # Create the medical record
        medical_record = MedicalRecord.objects.create(
            patient=patient,
            doctor=doctor,
            appointment=appointment,
            vital_signs=vital_signs,
            **validated_data
        )
        
        return medical_record


class NotificationSerializer(serializers.ModelSerializer):
    """
    Serializer for Notification model
    Includes sender profile information
    """
    sender_info = serializers.SerializerMethodField()
    created_at_formatted = serializers.SerializerMethodField()
    
    class Meta:
        model = Notification
        fields = [
            'id',
            'title',
            'message',
            'is_read',
            'created_at',
            'created_at_formatted',
            'sender',
            'sender_info'
        ]
        read_only_fields = ['created_at', 'is_read']
    
    def get_sender_info(self, obj):
        """Include sender's information"""
        if not obj.sender:
            return None
            
        sender = obj.sender
        profile = getattr(sender, 'profile', None)
        
        # Get first_name and last_name from the User model, not profile
        first_name = getattr(sender, 'first_name', '')
        last_name = getattr(sender, 'last_name', '')
        full_name = f"{first_name} {last_name}".strip() or sender.email.split('@')[0]
        
        return {
            'id': sender.id,
            'email': sender.email,
            'first_name': first_name,
            'last_name': last_name,
            'full_name': full_name,
            'profile_picture': self.get_profile_picture_url(profile) if profile else None
        }
    
    def get_created_at_formatted(self, obj):
        """Return formatted date string"""
        return obj.created_at.strftime('%b %d, %Y %I:%M %p')
    
    def get_profile_picture_url(self, profile):
        """Return full URL for profile picture"""
        if profile and profile.profile_picture:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(profile.profile_picture.url)
            return profile.profile_picture.url
        return None


class ProfileSerializer(serializers.ModelSerializer):
    profile_picture_url = serializers.SerializerMethodField()
    document_1_url = serializers.SerializerMethodField()
    document_2_url = serializers.SerializerMethodField()
    document_3_url = serializers.SerializerMethodField()
    document_4_url = serializers.SerializerMethodField()
    department_name = serializers.SerializerMethodField()
    
    def validate_date_of_birth(self, value):
        """Convert empty string to None for date_of_birth"""
        if value == '':
            return None
        return value
    
    def validate_employment_date(self, value):
        """Convert empty string to None for employment_date"""
        if value == '':
            return None
        return value
    
    def validate_department(self, value):
        """Convert empty string to None or handle department name lookup"""
        if value == '':
            return None
        
        # If value is a string (department name), look up the department
        if isinstance(value, str):
            try:
                department = Department.objects.get(name=value)
                return department
            except Department.DoesNotExist:
                raise serializers.ValidationError(f"Department '{value}' does not exist")
        
        # If value is already a Department instance or ID, return as is
        return value
    
    class Meta:
        model = Profile
        fields = [
            'phone_number',
            'address',
            'date_of_birth',
            'gender',
            'marital_status',
            'blood_group',
            'genotype',
            'national_id',
            'emergency_contact',
            'next_of_kin',
            'relationship_to_next_of_kin',
            'profile_picture',
            'profile_picture_url',
            'document_1',
            'document_1_url',
            'document_2',
            'document_2_url',
            'document_3',
            'document_3_url',
            'document_4',
            'document_4_url',
            'specialization',
            'license_number',
            'department',
            'department_name',
            'employment_date',
            'qualification',
            'bio',
            'created_at',
            'updated_at',
        ]
        extra_kwargs = {
            'profile_picture': {'required': False, 'write_only': True},
            'document_1': {'required': False, 'write_only': True},
            'document_2': {'required': False, 'write_only': True},
            'document_3': {'required': False, 'write_only': True},
            'document_4': {'required': False, 'write_only': True},
            'department': {'required': False, 'write_only': True},
            'created_at': {'read_only': True},
            'updated_at': {'read_only': True}
        }
    
    def get_profile_picture_url(self, obj):
        """Return full URL for profile picture"""
        if obj.profile_picture:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.profile_picture.url)
            return obj.profile_picture.url
        return None
    
    def get_document_1_url(self, obj):
        """Return full URL for document_1"""
        if obj.document_1:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.document_1.url)
            return obj.document_1.url
        return None
    
    def get_document_2_url(self, obj):
        """Return full URL for document_2"""
        if obj.document_2:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.document_2.url)
            return obj.document_2.url
        return None
    
    def get_document_3_url(self, obj):
        """Return full URL for document_3"""
        if obj.document_3:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.document_3.url)
            return obj.document_3.url
        return None
    
    def get_document_4_url(self, obj):
        """Return full URL for document_4"""
        if obj.document_4:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.document_4.url)
            return obj.document_4.url
        return None
    
    def get_department_name(self, obj):
        """Return department name"""
        if obj.department:
            return obj.department.name
        return None



class UserProfileSerializer(serializers.ModelSerializer):
    profile = serializers.SerializerMethodField()
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
            'profile'
        ]
    
    def get_profile(self, obj):
        """Return profile with request context for full URLs"""
        if hasattr(obj, 'profile'):
            return ProfileSerializer(obj.profile, context=self.context).data
        return None
    
    def get_role(self, obj):
        return obj.role.name if obj.role else None
    
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"



class DepartmentSerializer(serializers.ModelSerializer):
    total_staff = serializers.SerializerMethodField()
    total_patients = serializers.SerializerMethodField()
    
    class Meta:
        model = Department
        fields = ['id', 'name', 'description', 'total_staff', 'total_patients']
    
    def get_total_staff(self, obj):
        return obj.profiles.filter(user__role__name__in=['doctor', 'nurse']).count()
    
    def get_total_patients(self, obj):
        return obj.profiles.filter(user__role__name='patient').count()



class DoctorListSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    department = serializers.SerializerMethodField()
    profile_picture = serializers.SerializerMethodField()
    specialization = serializers.SerializerMethodField()
    phone_number = serializers.SerializerMethodField()
    bio = serializers.SerializerMethodField()
    education = serializers.SerializerMethodField()
    experience = serializers.SerializerMethodField()
    consultation_fee = serializers.SerializerMethodField()
    available_hours = serializers.SerializerMethodField()

    class Meta:
        model = get_user_model()
        fields = '__all__'

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"

    def get_department(self, obj):
        if hasattr(obj, 'profile') and obj.profile and obj.profile.department:
            return {
                'id': obj.profile.department.id,
                'name': obj.profile.department.name,
                'description': obj.profile.department.description
            }
        return None

    def get_profile_picture(self, obj):
        if hasattr(obj, 'profile') and obj.profile and obj.profile.profile_picture:
            request = self.context.get('request')
            if request is not None:
                return request.build_absolute_uri(obj.profile.profile_picture.url)
            return obj.profile.profile_picture.url
        return None

    def get_specialization(self, obj):
        return getattr(obj.profile, 'specialization', None) if hasattr(obj, 'profile') else None

    def get_phone_number(self, obj):
        return getattr(obj.profile, 'phone_number', None) if hasattr(obj, 'profile') else None

    def get_bio(self, obj):
        return getattr(obj.profile, 'bio', None) if hasattr(obj, 'profile') else None

    def get_education(self, obj):
        return getattr(obj.profile, 'education', None) if hasattr(obj, 'profile') else None

    def get_experience(self, obj):
        return getattr(obj.profile, 'experience', None) if hasattr(obj, 'profile') else None

    def get_consultation_fee(self, obj):
        return getattr(obj.profile, 'consultation_fee', None) if hasattr(obj, 'profile') else None

    def get_available_hours(self, obj):
        if hasattr(obj, 'profile') and hasattr(obj.profile, 'available_hours'):
            return obj.profile.available_hours
        return None



class BookAppointmentSerializer(serializers.ModelSerializer):
    doctor_id = serializers.IntegerField(write_only=True)
    appointment_date = serializers.DateTimeField()

    class Meta:
        model = Appointment
        fields = ['doctor_id', 'appointment_date', 'patient_reason_for_appointment']

    def validate(self, data):
        User = get_user_model()
        
        # Ensure the selected doctor exists and is a doctor
        try:
            doctor = User.objects.get(
                id=data['doctor_id'],
                role__name='doctor'
            )
            data['doctor'] = doctor
        except User.DoesNotExist:
            raise serializers.ValidationError(
                {"doctor_id": "Doctor not found or invalid."}
            )

        # Ensure appointment is in the future
        if data['appointment_date'] <= timezone.now():
            raise serializers.ValidationError(
                {"appointment_date": "Appointment date must be in the future."}
            )

        # Check for existing appointment at same time
        if Appointment.objects.filter(
            doctor=doctor,
            appointment_date=data['appointment_date'],
            status__in=['pending', 'confirmed']
        ).exists():
            raise serializers.ValidationError(
                {"appointment_date": "This time slot is already booked."}
            )

        return data

    def create(self, validated_data):
        return Appointment.objects.create(
            patient=self.context['request'].user,
            doctor=validated_data['doctor'],
            appointment_date=validated_data['appointment_date'],
            patient_reason_for_appointment=validated_data.get('patient_reason_for_appointment', ''),
            status='pending'
        )



# In healthManagement/serializers.py, add this after the BookAppointmentSerializer
class PatientAppointmentSerializer(serializers.ModelSerializer):
    doctor_name = serializers.SerializerMethodField()
    doctor_specialization = serializers.SerializerMethodField()
    doctor_profile_picture = serializers.SerializerMethodField()
    department_name = serializers.SerializerMethodField()
    formatted_date = serializers.SerializerMethodField()
    time_until_appointment = serializers.SerializerMethodField()
    is_upcoming = serializers.SerializerMethodField()
    is_past = serializers.SerializerMethodField()

    class Meta:
        model = Appointment
        fields = [
            'id',
            'appointment_date',
            'formatted_date',
            'time_until_appointment',
            'status',
            'patient_reason_for_appointment',
            'created_at',
            'updated_at',
            'doctor_id',
            'doctor_name',
            'doctor_specialization',
            'doctor_profile_picture',
            'department_name',
            'is_upcoming',
            'is_past',
            'is_patient_available',
            'is_vitals_taken',
            'is_doctor_done_with_patient',
            'is_doctor_with_patient',
        ]
        read_only_fields = fields

    def get_doctor_name(self, obj):
        return f"{obj.doctor.first_name} {obj.doctor.last_name}"

    def get_doctor_specialization(self, obj):
        return getattr(obj.doctor.profile, 'specialization', None) if hasattr(obj.doctor, 'profile') else None

    def get_doctor_profile_picture(self, obj):
        if hasattr(obj.doctor, 'profile') and obj.doctor.profile and obj.doctor.profile.profile_picture:
            request = self.context.get('request')
            if request is not None:
                return request.build_absolute_uri(obj.doctor.profile.profile_picture.url)
            return obj.doctor.profile.profile_picture.url
        return None

    def get_department_name(self, obj):
        if hasattr(obj.doctor, 'profile') and obj.doctor.profile and obj.doctor.profile.department:
            return obj.doctor.profile.department.name
        return None

    def get_formatted_date(self, obj):
        return obj.appointment_date.strftime('%B %d, %Y %I:%M %p')

    def get_time_until_appointment(self, obj):
        now = timezone.now()
        delta = obj.appointment_date - now
        
        if delta.days < 0:
            return "Past appointment"
        elif delta.days == 0:
            if delta.seconds < 3600:  # Less than 1 hour
                minutes = delta.seconds // 60
                return f"In {minutes} minute{'s' if minutes != 1 else ''}"
            else:
                hours = delta.seconds // 3600
                return f"Today in {hours} hour{'s' if hours != 1 else ''}"
        elif delta.days == 1:
            return "Tomorrow"
        elif delta.days < 7:
            return f"In {delta.days} days"
        else:
            return obj.appointment_date.strftime('%B %d, %Y')

    def get_is_upcoming(self, obj):
        return obj.appointment_date > timezone.now()

    def get_is_past(self, obj):
        return obj.appointment_date <= timezone.now()


class DoctorAppointmentSerializer(serializers.ModelSerializer):
    """
    Serializer for appointments from doctor's perspective
    Includes patient information and profile picture
    """
    patient_name = serializers.SerializerMethodField()
    patient_profile_picture = serializers.SerializerMethodField()
    patient_email = serializers.SerializerMethodField()
    patient_phone = serializers.SerializerMethodField()
    formatted_date = serializers.SerializerMethodField()
    time_until_appointment = serializers.SerializerMethodField()
    is_upcoming = serializers.SerializerMethodField()
    is_past = serializers.SerializerMethodField()

    class Meta:
        model = Appointment
        fields = [
            'id',
            'appointment_date',
            'formatted_date',
            'time_until_appointment',
            'status',
            'patient_reason_for_appointment',
            'created_at',
            'updated_at',
            'patient_id',
            'patient_name',
            'patient_email',
            'patient_phone',
            'patient_profile_picture',
            'is_upcoming',
            'is_past',
            'is_patient_available',
            'is_vitals_taken',
            'is_doctor_done_with_patient',
            'is_doctor_with_patient',
        ]
        read_only_fields = fields

    def get_patient_name(self, obj):
        return f"{obj.patient.first_name} {obj.patient.last_name}"

    def get_patient_profile_picture(self, obj):
        if hasattr(obj.patient, 'profile') and obj.patient.profile and obj.patient.profile.profile_picture:
            request = self.context.get('request')
            if request is not None:
                return request.build_absolute_uri(obj.patient.profile.profile_picture.url)
            return obj.patient.profile.profile_picture.url
        return None

    def get_patient_email(self, obj):
        return obj.patient.email

    def get_patient_phone(self, obj):
        if hasattr(obj.patient, 'profile') and obj.patient.profile:
            return obj.patient.profile.phone_number
        return None

    def get_formatted_date(self, obj):
        return obj.appointment_date.strftime('%B %d, %Y %I:%M %p')

    def get_time_until_appointment(self, obj):
        now = timezone.now()
        delta = obj.appointment_date - now
        
        if delta.days < 0:
            return "Past appointment"
        elif delta.days == 0:
            if delta.seconds < 3600:  # Less than 1 hour
                minutes = delta.seconds // 60
                return f"In {minutes} minute{'s' if minutes != 1 else ''}"
            else:
                hours = delta.seconds // 3600
                return f"Today in {hours} hour{'s' if hours != 1 else ''}"
        elif delta.days == 1:
            return "Tomorrow"
        elif delta.days < 7:
            return f"In {delta.days} days"
        else:
            return obj.appointment_date.strftime('%B %d, %Y')

    def get_is_upcoming(self, obj):
        return obj.appointment_date > timezone.now()

    def get_is_past(self, obj):
        return obj.appointment_date <= timezone.now()


class AppointmentDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for a single appointment
    Includes complete patient and doctor information with profiles
    """
    # Patient information
    patient_info = serializers.SerializerMethodField()
    
    # Doctor information
    doctor_info = serializers.SerializerMethodField()
    
    # Nurse information (if assigned)
    nurse_info = serializers.SerializerMethodField()
    
    # Formatted fields
    formatted_date = serializers.SerializerMethodField()
    time_until_appointment = serializers.SerializerMethodField()
    is_upcoming = serializers.SerializerMethodField()
    is_past = serializers.SerializerMethodField()

    class Meta:
        model = Appointment
        fields = [
            'id',
            'appointment_date',
            'formatted_date',
            'time_until_appointment',
            'status',
            'patient_reason_for_appointment',
            'created_at',
            'updated_at',
            'patient_info',
            'doctor_info',
            'nurse_info',
            'is_upcoming',
            'is_past',
            'is_patient_available',
            'is_vitals_taken',
            'is_doctor_done_with_patient',
            'is_doctor_with_patient',
            'is_medical_history_recorded',
        ]
        read_only_fields = fields

    def get_patient_info(self, obj):
        """Get complete patient information including profile"""
        patient = obj.patient
        profile = getattr(patient, 'profile', None)
        
        patient_data = {
            'id': patient.id,
            'email': patient.email,
            'first_name': patient.first_name,
            'last_name': patient.last_name,
            'full_name': f"{patient.first_name} {patient.last_name}",
        }
        
        if profile:
            request = self.context.get('request')
            patient_data['profile'] = {
                'phone_number': profile.phone_number,
                'date_of_birth': profile.date_of_birth.strftime('%Y-%m-%d') if profile.date_of_birth else None,
                'gender': profile.gender,
                'address': profile.address,
                'marital_status': profile.marital_status,
                'blood_group': profile.blood_group,
                'genotype': profile.genotype,
                'national_id': profile.national_id,
                'emergency_contact': profile.emergency_contact,
                'next_of_kin': profile.next_of_kin,
                'relationship_to_next_of_kin': profile.relationship_to_next_of_kin,
                'is_admitted': profile.is_admitted,
                'profile_picture': None
            }
            
            # Add profile picture URL if available
            if profile.profile_picture:
                if request:
                    patient_data['profile']['profile_picture'] = request.build_absolute_uri(profile.profile_picture.url)
                else:
                    patient_data['profile']['profile_picture'] = profile.profile_picture.url
        
        return patient_data

    def get_doctor_info(self, obj):
        """Get complete doctor information including profile"""
        doctor = obj.doctor
        profile = getattr(doctor, 'profile', None)
        
        doctor_data = {
            'id': doctor.id,
            'email': doctor.email,
            'first_name': doctor.first_name,
            'last_name': doctor.last_name,
            'full_name': f"{doctor.first_name} {doctor.last_name}",
        }
        
        if profile:
            request = self.context.get('request')
            doctor_data['profile'] = {
                'phone_number': profile.phone_number,
                'specialization': profile.specialization,
                'bio': profile.bio,
                'license_number': profile.license_number,
                'qualification': profile.qualification,
                'employment_date': profile.employment_date.strftime('%Y-%m-%d') if profile.employment_date else None,
                'department': profile.department.name if profile.department else None,
                'profile_picture': None
            }
            
            # Add profile picture URL if available
            if profile.profile_picture:
                if request:
                    doctor_data['profile']['profile_picture'] = request.build_absolute_uri(profile.profile_picture.url)
                else:
                    doctor_data['profile']['profile_picture'] = profile.profile_picture.url
        
        return doctor_data

    def get_nurse_info(self, obj):
        """Get nurse information if assigned"""
        if not obj.nurse:
            return None
            
        nurse = obj.nurse
        profile = getattr(nurse, 'profile', None)
        
        nurse_data = {
            'id': nurse.id,
            'email': nurse.email,
            'first_name': nurse.first_name,
            'last_name': nurse.last_name,
            'full_name': f"{nurse.first_name} {nurse.last_name}",
        }
        
        if profile:
            request = self.context.get('request')
            nurse_data['profile'] = {
                'phone_number': profile.phone_number,
                'profile_picture': None
            }
            
            # Add profile picture URL if available
            if profile.profile_picture:
                if request:
                    nurse_data['profile']['profile_picture'] = request.build_absolute_uri(profile.profile_picture.url)
                else:
                    nurse_data['profile']['profile_picture'] = profile.profile_picture.url
        
        return nurse_data

    def get_formatted_date(self, obj):
        return obj.appointment_date.strftime('%B %d, %Y %I:%M %p')

    def get_time_until_appointment(self, obj):
        now = timezone.now()
        delta = obj.appointment_date - now
        
        if delta.days < 0:
            return "Past appointment"
        elif delta.days == 0:
            if delta.seconds < 3600:  # Less than 1 hour
                minutes = delta.seconds // 60
                return f"In {minutes} minute{'s' if minutes != 1 else ''}"
            else:
                hours = delta.seconds // 3600
                return f"Today in {hours} hour{'s' if hours != 1 else ''}"
        elif delta.days == 1:
            return "Tomorrow"
        elif delta.days < 7:
            return f"In {delta.days} days"
        else:
            return obj.appointment_date.strftime('%B %d, %Y')

    def get_is_upcoming(self, obj):
        return obj.appointment_date > timezone.now()

    def get_is_past(self, obj):
        return obj.appointment_date <= timezone.now()


class TreatmentSerializer(serializers.ModelSerializer):
    """
    Serializer for Treatment model
    """
    medical_record_id = serializers.IntegerField(write_only=True)
    prescribed_by_id = serializers.IntegerField(write_only=True, required=False)
    prescribed_by_info = serializers.SerializerMethodField()
    treatment_type_display = serializers.CharField(source='get_treatment_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    patient_info = serializers.SerializerMethodField()
    
    class Meta:
        model = Treatment
        fields = [
            'id', 'medical_record_id', 'medical_record', 'treatment_type', 'treatment_type_display',
            'name', 'start_date', 'end_date', 'status', 'status_display', 'notes',
            'prescribed_by', 'prescribed_by_id', 'prescribed_by_info', 'patient_info',
            'date_created', 'last_updated'
        ]
        read_only_fields = ['prescribed_by', 'date_created', 'last_updated']
    
    def get_prescribed_by_info(self, obj):
        """Get doctor information who prescribed the treatment"""
        if not obj.prescribed_by:
            return None
            
        doctor = obj.prescribed_by
        profile = getattr(doctor, 'profile', None)
        
        return {
            'id': doctor.id,
            'email': doctor.email,
            'first_name': doctor.first_name,
            'last_name': doctor.last_name,
            'full_name': f"{doctor.first_name} {doctor.last_name}",
            'specialization': getattr(profile, 'specialization', None) if profile else None,
            'phone_number': getattr(profile, 'phone_number', None) if profile else None
        }
        
    def get_patient_info(self, obj):
        """Get patient information from the medical record"""
        if not hasattr(obj, 'medical_record') or not obj.medical_record:
            return None
            
        patient = obj.medical_record.patient
        if not patient:
            return None
            
        profile = getattr(patient, 'profile', None)
        
        return {
            'id': patient.id,
            'email': patient.email,
            'first_name': patient.first_name,
            'last_name': patient.last_name,
            'full_name': f"{patient.first_name} {patient.last_name}",
            'phone_number': getattr(profile, 'phone_number', None) if profile else None,
            'date_of_birth': getattr(profile, 'date_of_birth', None) if profile else None,
            'gender': getattr(profile, 'gender', None) if profile else None,
            'blood_group': getattr(profile, 'blood_group', None) if profile else None,
            'genotype': getattr(profile, 'genotype', None) if profile else None
        }
    
    def validate_medical_record_id(self, value):
        """Validate that the medical record exists"""
        try:
            return MedicalRecord.objects.get(id=value)
        except MedicalRecord.DoesNotExist:
            raise ValidationError("Medical record not found.")
    
    def validate_prescribed_by_id(self, value):
        """Validate that the prescribed_by user exists and is a doctor"""
        if value is None:
            return None
            
        try:
            doctor = APPLICATIONS_USER_MODEL.objects.get(
                id=value,
                role__name='doctor',
                is_active=True
            )
            return doctor
        except APPLICATIONS_USER_MODEL.DoesNotExist:
            raise ValidationError("Doctor not found or is not active.")
    
    def create(self, validated_data):
        """Create a new treatment and update the medical record's is_treatment_created field"""
        # Get the medical record
        medical_record = validated_data.get('medical_record_id')
        if not isinstance(medical_record, MedicalRecord):
            medical_record = MedicalRecord.objects.get(id=medical_record)
        
        # Create the treatment
        treatment = Treatment.objects.create(
            medical_record=medical_record,
            **{k: v for k, v in validated_data.items() if k != 'medical_record_id'}
        )
        
        # Update the medical record's is_treatment_created field
        if not medical_record.is_treatment_created:
            medical_record.is_treatment_created = True
            medical_record.save(update_fields=['is_treatment_created'])
        
        return treatment
        
    def validate(self, data):
        """Validate the treatment data"""
        # Set the prescribed_by to the request user if not provided
        if 'prescribed_by_id' not in data and 'request' in self.context:
            request = self.context['request']
            if hasattr(request, 'user') and request.user.is_authenticated:
                data['prescribed_by_id'] = request.user.id
        
        # Ensure end_date is after start_date if both are provided
        if 'start_date' in data and 'end_date' in data and data['end_date']:
            if data['end_date'] < data['start_date']:
                raise ValidationError({"end_date": "End date must be after start date."})
                
        return data
    
    def create(self, validated_data):
        """Create a new treatment and update the medical record's is_treatment_created field"""
        # Extract the medical_record and prescribed_by from the validated data
        medical_record = validated_data.pop('medical_record_id', None)
        if medical_record:
            if not isinstance(medical_record, MedicalRecord):
                medical_record = MedicalRecord.objects.get(id=medical_record)
            validated_data['medical_record'] = medical_record
            
        prescribed_by = validated_data.pop('prescribed_by_id', None)
        if prescribed_by:
            validated_data['prescribed_by'] = prescribed_by
            
        # Create the treatment
        treatment = super().create(validated_data)
        
        # Update the medical record's is_treatment_created field
        if medical_record and not medical_record.is_treatment_created:
            medical_record.is_treatment_created = True
            medical_record.save(update_fields=['is_treatment_created'])
            
        return treatment


class SurgeryPlacementSerializer(serializers.ModelSerializer):
    """
    Serializer for SurgeryPlacement model
    """
    treatment_id = serializers.IntegerField(write_only=True)
    medical_record_id = serializers.IntegerField(write_only=True)
    surgeon_id = serializers.IntegerField(write_only=True, required=False)
    patient_id = serializers.IntegerField(write_only=True, required=False)
    
    treatment_info = serializers.SerializerMethodField(read_only=True)
    medical_record_info = serializers.SerializerMethodField(read_only=True)
    surgeon_info = serializers.SerializerMethodField(read_only=True)
    patient_info = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = SurgeryPlacement
        fields = [
            'id', 'treatment_id', 'medical_record_id', 'surgeon_id', 'patient_id',
            'treatment_info', 'medical_record_info', 'surgeon_info', 'patient_info',
            'surgery_type', 'scheduled_date', 'status', 'notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_treatment_info(self, obj):
        """Return basic treatment information"""
        return {
            'id': obj.treatment.id,
            'name': obj.treatment.name,
            'treatment_type': obj.treatment.get_treatment_type_display(),
            'status': obj.treatment.get_status_display(),
        }
    
    def get_medical_record_info(self, obj):
        """Return basic medical record information"""
        return {
            'id': obj.medical_record.id,
            'diagnosis': obj.medical_record.diagnosis,
            'status': obj.medical_record.get_status_display(),
            'patient_name': f"{obj.medical_record.patient.first_name} {obj.medical_record.patient.last_name}",
            'patient_id': obj.medical_record.patient.id
        }
        
    def get_patient_info(self, obj):
        """Return basic patient information"""
        if not obj.patient:
            return None
        return {
            'id': obj.patient.id,
            'name': f"{obj.patient.first_name} {obj.patient.last_name}",
            'email': obj.patient.email,
            'phone_number': getattr(obj.patient.profile, 'phone_number', None)
        }
    
    def get_surgeon_info(self, obj):
        """Return basic surgeon information"""
        if not obj.surgeon:
            return None
        return {
            'id': obj.surgeon.id,
            'name': f"{obj.surgeon.first_name} {obj.surgeon.last_name}",
            'email': obj.surgeon.email
        }
    
    def validate_treatment_id(self, value):
        """Validate that the treatment exists and is of type 'surgery'"""
        try:
            treatment = Treatment.objects.get(id=value)
            if treatment.treatment_type != 'surgery':
                raise serializers.ValidationError("The specified treatment is not a surgery type.")
            return treatment
        except Treatment.DoesNotExist:
            raise serializers.ValidationError("Treatment not found.")
    
    def validate_medical_record_id(self, value):
        """Validate that the medical record exists"""
        try:
            medical_record = MedicalRecord.objects.get(id=value)
            
            # If patient_id is provided, validate that the medical record belongs to this patient
            patient_id = self.initial_data.get('patient_id')
            if patient_id and str(medical_record.patient_id) != str(patient_id):
                raise serializers.ValidationError("The medical record does not belong to the specified patient.")
                
            return medical_record
        except MedicalRecord.DoesNotExist:
            raise serializers.ValidationError("Medical record not found.")
    
    def validate_surgeon_id(self, value):
        """Validate that the surgeon exists and is a doctor"""
        if not value:
            return None
        try:
            surgeon = APPLICATIONS_USER_MODEL.objects.get(
                id=value,
                role__name='doctor',
                is_active=True
            )
            return surgeon
        except APPLICATIONS_USER_MODEL.DoesNotExist:
            raise serializers.ValidationError("Surgeon not found or is not an active doctor.")
    
    def validate_patient_id(self, value):
        """Validate that the patient exists and is a patient"""
        try:
            patient = APPLICATIONS_USER_MODEL.objects.get(
                id=value,
                role__name='patient',
                is_active=True
            )
            return patient
        except APPLICATIONS_USER_MODEL.DoesNotExist:
            raise serializers.ValidationError("Patient not found or is not an active patient.")
    
    def create(self, validated_data):
        """Create a new surgery placement"""
        # Remove the IDs from validated_data as they're not direct fields
        treatment = validated_data.pop('treatment_id')
        medical_record = validated_data.pop('medical_record_id')
        surgeon = validated_data.pop('surgeon_id', None)
        patient = validated_data.pop('patient_id', None)
        
        # If patient is not provided, use the one from the medical record
        if not patient and medical_record:
            patient = medical_record.patient
        
        # Create the surgery placement
        surgery_placement = SurgeryPlacement.objects.create(
            treatment=treatment,
            medical_record=medical_record,
            surgeon=surgeon,
            patient=patient,
            **validated_data
        )
        
        return surgery_placement


class VitalSignSerializer(serializers.ModelSerializer):
    """
    Serializer for VitalSign model
    Includes patient and recorded_by information
    """
    patient_info = serializers.SerializerMethodField()
    recorded_by_info = serializers.SerializerMethodField()
    bmi = serializers.SerializerMethodField()
    blood_pressure = serializers.SerializerMethodField()
    recorded_at_formatted = serializers.SerializerMethodField()
    
    class Meta:
        model = VitalSign
        fields = [
            'id',
            'patient',
            'patient_info',
            'recorded_by',
            'recorded_by_info',
            'recorded_at',
            'recorded_at_formatted',
            'temperature_c',
            'pulse_rate',
            'respiratory_rate',
            'systolic_bp',
            'diastolic_bp',
            'blood_pressure',
            'oxygen_saturation',
            'weight_kg',
            'height_cm',
            'bmi',
            'notes'
        ]
        read_only_fields = ['recorded_at', 'recorded_by']
    
    def get_patient_info(self, obj):
        """Include patient's basic information"""
        if not obj.patient:
            return None
        
        patient = obj.patient
        return {
            'id': patient.id,
            'email': patient.email,
            'first_name': patient.first_name,
            'last_name': patient.last_name,
            'full_name': f"{patient.first_name} {patient.last_name}".strip()
        }
    
    def get_recorded_by_info(self, obj):
        """Include recorded_by (nurse/doctor) information"""
        if not obj.recorded_by:
            return None
        
        recorder = obj.recorded_by
        return {
            'id': recorder.id,
            'email': recorder.email,
            'first_name': recorder.first_name,
            'last_name': recorder.last_name,
            'full_name': f"{recorder.first_name} {recorder.last_name}".strip(),
            'role': recorder.role.name if hasattr(recorder, 'role') and recorder.role else None
        }
    
    def get_bmi(self, obj):
        """Get calculated BMI"""
        return obj.bmi()
    
    def get_blood_pressure(self, obj):
        """Format blood pressure as systolic/diastolic"""
        return f"{obj.systolic_bp}/{obj.diastolic_bp}"
    
    def get_recorded_at_formatted(self, obj):
        """Format recorded_at timestamp"""
        return obj.recorded_at.strftime('%B %d, %Y %I:%M %p')


class TestRequestListSerializer(serializers.ModelSerializer):
    """Serializer for listing test requests with related information"""
    patient_name = serializers.SerializerMethodField()
    doctor_name = serializers.SerializerMethodField()
    lab_technician_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display')
    test_type = TestTypesSerializer(read_only=True)
    
    class Meta:
        model = TestRequest
        fields = [
            'id', 'test_type', 'test_name', 'status', 'status_display',
            'notes', 'created_at', 'updated_at', 'patient_name', 'doctor_name',
            'lab_technician_name', 'customers_name', 'customers_phone', 'customers_email',
            'requested_by', 'is_payment_done', 'payment_received_by', 'payment_method', 'status'
        ]
        read_only_fields = fields
    
    def get_patient_name(self, obj):
        return f"{obj.patient.first_name} {obj.patient.last_name}" if obj.patient else obj.customers_name
    
    def get_doctor_name(self, obj):
        return f"{obj.requested_by.first_name} {obj.requested_by.last_name}" if obj.requested_by else None
    
    def get_lab_technician_name(self, obj):
        if obj.lab_tehnician:
            return f"{obj.lab_tehnician.first_name} {obj.lab_tehnician.last_name}"
        return None
    
    def get_requested_by(self, obj):
        if obj.requested_by:
            return f"{obj.requested_by.first_name} {obj.requested_by.last_name}"
        return None




class TestRequestSerializer(serializers.ModelSerializer):
    patient_id = serializers.IntegerField(write_only=True, required=False)
    requested_by_id = serializers.IntegerField(write_only=True, required=False)
    medical_record_id = serializers.IntegerField(write_only=True, required=False)
    customer_name = serializers.CharField(write_only=True, required=False)
    customer_phone = serializers.CharField(write_only=True, required=False)
    customer_email = serializers.EmailField(write_only=True, required=False)
    
    class Meta:
        model = TestRequest
        fields = [
            'id',
            'patient',
            'patient_id',
            'customers_name',
            'customers_phone',
            'customers_email',
            'customer_name',
            'customer_phone',
            'customer_email',
            'medical_record',
            'medical_record_id',
            'test_type',
            'test_name',
            'requested_by',
            'requested_by_id',
            'lab_tehnician',
            'status',
            'notes',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
        
    def create(self, validated_data):
        patient_id = validated_data.pop('patient_id', None)
        requested_by_id = validated_data.pop('requested_by_id', None)
        medical_record_id = validated_data.pop('medical_record_id', None)
        
        # Handle customer fields that might come with different field names
        customer_name = validated_data.pop('customer_name', None)
        customer_phone = validated_data.pop('customer_phone', None)
        customer_email = validated_data.pop('customer_email', None)
        
        # Map customer fields to the correct model fields
        if customer_name:
            validated_data['customers_name'] = customer_name
        if customer_phone:
            validated_data['customers_phone'] = customer_phone
        if customer_email:
            validated_data['customers_email'] = customer_email
        
        if patient_id:
            validated_data['patient_id'] = patient_id
        if requested_by_id:
            validated_data['requested_by_id'] = requested_by_id
        if medical_record_id:
            validated_data['medical_record_id'] = medical_record_id
            
        return super().create(validated_data)





class PatientProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields ='__all__'
        read_only_fields = ['id']

class MedicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicalRecord
        fields = ['id', 'name', 'dosage', 'frequency', 'start_date', 'end_date', 'prescribed_by', 'notes']

class PatientMedicationSerializer(serializers.ModelSerializer):
    """
    Serializer for patient medications from Treatment model
    """
    treatment_type_display = serializers.CharField(source='get_treatment_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    prescriber_detail = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = Treatment
        fields = '__all__'
        read_only_fields = ['date_created', 'last_updated']
    
    def get_prescriber_detail(self, obj):
        if not obj.prescribed_by:
            return None
        return {
            'id': obj.prescribed_by.id,
            'email': obj.prescribed_by.email,
            'first_name': obj.prescribed_by.first_name,
            'last_name': obj.prescribed_by.last_name,
            'full_name': f"{obj.prescribed_by.first_name or ''} {obj.prescribed_by.last_name or ''}".strip() or obj.prescribed_by.email
        }

class AdmissionSerializer(serializers.ModelSerializer):
    ward = serializers.StringRelatedField()
    room = serializers.StringRelatedField()
    bed = serializers.StringRelatedField()
    
    class Meta:
        model = Admission
        fields = ['id', 'admission_date', 'discharge_date', 'ward', 'room', 'bed', 'reason', 'status']

class PatientUserSerializer(serializers.ModelSerializer):
    profile = PatientProfileSerializer(read_only=True)
    full_name = serializers.SerializerMethodField()
    current_medications = serializers.SerializerMethodField()
    current_admission = serializers.SerializerMethodField()
    
    class Meta:
        model = APPLICATIONS_USER_MODEL
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'is_active', 'date_joined', 'profile', 'current_medications',
            'current_admission'
        ]
        read_only_fields = ['id', 'email', 'date_joined', 'is_active']
    
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"
    
    def get_current_medications(self, obj):
        # Get active medications from the patient's medical records
        from django.utils import timezone
        today = timezone.now().date()
        
        # Get all treatments that are medications and not completed
        treatments = Treatment.objects.filter(
            medical_record__patient=obj,
            treatment_type='medication',
            status__in=['prescribed', 'in_progress'],
            end_date__isnull=True  # Medication is still active
        ).select_related('prescribed_by')
        
        # Convert treatments to medication format
        medications = []
        for treatment in treatments:
            # Safely get the prescribed by name
            prescribed_by_name = None
            if treatment.prescribed_by:
                # Try to get full name, first_name + last_name, or fall back to email/username
                user = treatment.prescribed_by
                if hasattr(user, 'get_full_name') and callable(user.get_full_name):
                    prescribed_by_name = user.get_full_name()
                elif hasattr(user, 'first_name') and hasattr(user, 'last_name'):
                    name_parts = [user.first_name or '', user.last_name or '']
                    prescribed_by_name = ' '.join(part for part in name_parts if part).strip() or user.email or user.username
                else:
                    prescribed_by_name = user.email or user.username

            medication_data = {
                'id': treatment.id,
                'name': treatment.name,
                'start_date': treatment.start_date,
                'end_date': treatment.end_date,
                'prescribed_by': prescribed_by_name,
                'notes': treatment.notes,
                'status': treatment.get_status_display(),
                'treatment_type': treatment.get_treatment_type_display()
            }
            
            # Add additional fields if they exist in the model
            if hasattr(treatment, 'dosage'):
                medication_data['dosage'] = treatment.dosage
            if hasattr(treatment, 'frequency'):
                medication_data['frequency'] = treatment.frequency
                
            medications.append(medication_data)
            
        return medications
    
    def get_current_admission(self, obj):
        # Get current admission if any
        try:
            admission = Admission.objects.filter(
                patient=obj,
                status='admitted'
            ).select_related('bed__room__ward', 'patient', 'admitted_by').first()
            
            if not admission:
                return None
                
            # Manually build the admission data with related fields
            admission_data = {
                'id': admission.id,
                'admission_date': admission.admission_date,
                'discharge_date': admission.discharge_date,
                'status': admission.status,
                'bed': None,
                'room': None,
                'ward': None
            }
            
            # Include bed information if available
            if admission.bed:
                admission_data['bed'] = {
                    'id': admission.bed.id,
                    'bed_number': admission.bed.id  # Using id as bed_number if not available
                }
                
                # Include room information if available
                if hasattr(admission.bed, 'room'):
                    admission_data['room'] = {
                        'id': admission.bed.room.id,
                        'room_number': admission.bed.room.name if hasattr(admission.bed.room, 'name') else f"Room {admission.bed.room.id}"
                    }
                    
                    # Include ward information if available
                    if hasattr(admission.bed.room, 'ward'):
                        admission_data['ward'] = {
                            'id': admission.bed.room.ward.id,
                            'name': admission.bed.room.ward.name
                        }
            
            return admission_data
            
        except Exception as e:
            print(f"Error getting admission: {str(e)}")
            return None


class PharmacyReferralSerializer(serializers.ModelSerializer):
    """Serializer for creating pharmacy referrals"""
    patient_id = serializers.IntegerField(write_only=True)
    medical_record_id = serializers.IntegerField(write_only=True, required=True)
    referred_by_id = serializers.IntegerField(write_only=True, required=True)
    pharmacist_id = serializers.IntegerField(required=False, allow_null=True)
    drug_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=True,
        help_text='List of drug IDs to be included in the referral'
    )
    
    class Meta:
        model = PharmacyReferral
        fields = [
            'id', 'patient_id', 'medical_record_id', 'referred_by_id', 'pharmacist_id',
            'reason', 'drug_ids', 'have_pharmacist_despensed', 'have_patient_received',
            'created_at'
        ]
        read_only_fields = ['have_pharmacist_despensed', 'have_patient_received', 'created_at']
    
    def validate_patient_id(self, value):
    
        try:
            patient = APPLICATIONS_USER_MODEL.objects.get(id=value, role__name='patient')
            return patient
        except User.DoesNotExist:
            raise serializers.ValidationError("A valid patient ID is required")
    
    def validate_medical_record_id(self, value):
        try:
            medical_record = MedicalRecord.objects.get(id=value)
            return medical_record
        except MedicalRecord.DoesNotExist:
            raise serializers.ValidationError("A valid medical record ID is required")
    
    def validate_referred_by_id(self, value):
        
        try:
            doctor = APPLICATIONS_USER_MODEL.objects.get(id=value, role__name='doctor')
            return doctor
        except User.DoesNotExist:
            raise serializers.ValidationError("A valid doctor ID is required")
    
    def validate_pharmacist_id(self, value):
        if value is None:
            return None
            
        try:
            pharmacist = APPLICATIONS_USER_MODEL.objects.get(id=value, role__name='pharmacist')
            return pharmacist
        except User.DoesNotExist:
            raise serializers.ValidationError("A valid pharmacist ID is required")
    
    def validate_drug_ids(self, value):
        if not value:
            raise serializers.ValidationError("At least one drug ID is required")
        
        from .models import Drug
        existing_drugs = Drug.objects.filter(id__in=value)
        if len(existing_drugs) != len(value):
            raise serializers.ValidationError("One or more drug IDs are invalid")
        return value
    
    def create(self, validated_data):
        # Extract the many-to-many relationship data
        drug_ids = validated_data.pop('drug_ids', [])
        
        # Extract the patient and medical record objects
        patient = validated_data.pop('patient_id')
        medical_record = validated_data.pop('medical_record_id')
        referred_by = validated_data.pop('referred_by_id')
        pharmacist = validated_data.get('pharmacist_id')
        
        # Create the pharmacy referral
        referral = PharmacyReferral.objects.create(
            patient=patient,
            medical_record=medical_record,
            referred_by=referred_by,
            pharmacist=pharmacist,
            **validated_data
        )
        
        # Add the drugs to the many-to-many relationship
        if drug_ids:
            referral.drugs.set(drug_ids)
        
        # Update the medical record's sent_to_pharmacy field
        if not medical_record.sent_to_pharmacy:
            medical_record.sent_to_pharmacy = True
            medical_record.save(update_fields=['sent_to_pharmacy', 'last_updated'])
        
        return referral

class MedicationTreatmentSerializer(serializers.ModelSerializer):
    """
    Serializer for creating delivered medication treatments
    """
    treatment_id = serializers.IntegerField(write_only=True)
    medical_record_id = serializers.IntegerField(write_only=True)
    drug_id = serializers.IntegerField(write_only=True)
    item_quantity = serializers.IntegerField(default=1, write_only=True)
    prescribed_by_info = serializers.SerializerMethodField(read_only=True)
    treatment_info = serializers.SerializerMethodField(read_only=True)
    medical_record_info = serializers.SerializerMethodField(read_only=True)
    drug_info = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = DeliveredMedicationTreatment
        fields = [
            'id', 'treatment_id', 'medical_record_id', 'drug_id', 'item_quantity', 'prescribed_by',
            'description', 'dosage', 'frequency', 'duration', 'date_created',
            'treatment_info', 'medical_record_info', 'drug_info', 'prescribed_by_info'
        ]
        read_only_fields = ['id', 'date_created', 'treatment_info', 'medical_record_info', 'drug_info', 'prescribed_by_info', 'prescribed_by']

    def get_treatment_info(self, obj):
        """Return basic treatment information"""
        if hasattr(obj, 'treatment'):
            return {
                'id': obj.treatment.id,
                'name': obj.treatment.name,
                'treatment_type': obj.treatment.get_treatment_type_display(),
            }
        return None

    def get_medical_record_info(self, obj):
        """Return basic medical record information"""
        if hasattr(obj, 'medical_record'):
            return {
                'id': obj.medical_record.id,
                'diagnosis': obj.medical_record.diagnosis,
                'status': obj.medical_record.get_status_display(),
            }
        return None

    def get_drug_info(self, obj):
        """Return basic drug information"""
        if hasattr(obj, 'drug'):
            return {
                'id': obj.drug.id,
                'name': obj.drug.name,
                'dosage': obj.drug.dosage,
                'form': obj.drug.form,
            }
        return None
    
    def get_prescribed_by_info(self, obj):
        """Return basic prescribed_by information"""
        if hasattr(obj, 'prescribed_by') and obj.prescribed_by:
            return {
                'id': obj.prescribed_by.id,
                'name': f"{obj.prescribed_by.first_name} {obj.prescribed_by.last_name}",
                'email': obj.prescribed_by.email,
            }
        return None

    def validate_treatment_id(self, value):
        """Validate that the treatment exists"""
        try:
            return Treatment.objects.get(id=value)
        except Treatment.DoesNotExist:
            raise serializers.ValidationError("Treatment not found.")
    
    def validate_medical_record_id(self, value):
        """Validate that the medical record exists"""
        try:
            return MedicalRecord.objects.get(id=value)
        except MedicalRecord.DoesNotExist:
            raise serializers.ValidationError("Medical record not found.")
    
    def validate_drug_id(self, value):
        """Validate that the drug exists"""
        try:
            return Drug.objects.get(id=value)
        except Drug.DoesNotExist:
            raise serializers.ValidationError("Drug not found.")
    
    def validate(self, data):
        """Cross-field validation"""
        treatment = data.get('treatment_id')
        medical_record = data.get('medical_record_id')
        
        if treatment and medical_record:
            if treatment.medical_record_id != medical_record.id:
                raise serializers.ValidationError(
                    "Treatment does not belong to the specified medical record."
                )
        
        return data

    def create(self, validated_data):
        """Create a new delivered medication treatment"""
        # Extract the IDs
        treatment = validated_data.pop('treatment_id')
        medical_record = validated_data.pop('medical_record_id')
        drug = validated_data.pop('drug_id')
        
        # Get the item quantity from validated data
        item_quantity = validated_data.get('item_quantity', 1)
        
        # Create the delivered treatment
        delivered_treatment = DeliveredMedicationTreatment.objects.create(
            treatment=treatment,
            medical_record=medical_record,
            drug=drug,
            prescribed_by=self.context['request'].user,  # Set the prescribing doctor
            **validated_data
        )
        
        # Create or update pharmacy referral for this medical record
        try:
            # Get the doctor from context (the user creating this treatment)
            doctor = self.context.get('request', {}).user
            
            # Check if a pharmacy referral already exists for this medical record
            existing_referral = PharmacyReferral.objects.filter(
                medical_record=medical_record
            ).first()
            
            if existing_referral:
                # Add the new delivered treatment to existing referral's drugs
                existing_referral.drugs.add(delivered_treatment)
                
                # Create or update ReferralDispensedDrugItem
                self._create_or_update_referral_drug_item(existing_referral, drug, item_quantity)
                
                # Calculate and update total amount
                total_amount = self._calculate_total_amount(existing_referral)
                existing_referral.total_amount = str(total_amount)
                existing_referral.save()
                
                print(f"[INFO] Added delivered treatment {delivered_treatment.id} to existing pharmacy referral {existing_referral.id}")
                print(f"[INFO] Updated total amount to {total_amount}")
            else:
                # Create new pharmacy referral
                new_referral = PharmacyReferral.objects.create(
                    patient=medical_record.patient,
                    medical_record=medical_record,
                    referred_by=doctor,
                    reason=f"Medication treatment: {delivered_treatment.description or 'Prescribed medication'}",
                    total_amount=str(delivered_treatment.drug.price_for_each or 0)  # Initial amount
                )
                # Add the delivered treatment to the new referral
                new_referral.drugs.add(delivered_treatment)
                
                # Create ReferralDispensedDrugItem for new referral
                self._create_or_update_referral_drug_item(new_referral, drug, item_quantity)
                
                # Calculate total amount including this drug
                total_amount = self._calculate_total_amount(new_referral)
                new_referral.total_amount = str(total_amount)
                new_referral.save()
                
                print(f"[INFO] Created new pharmacy referral {new_referral.id} and added delivered treatment {delivered_treatment.id}")
                print(f"[INFO] Initial total amount: {total_amount}")
            
        except Exception as e:
            print(f"[ERROR] Failed to create/update pharmacy referral: {str(e)}")
            import traceback
            traceback.print_exc()
            # Continue without failing the whole operation if referral creation fails
        
        # Update the medical record's sent_to_pharmacy field
        if not medical_record.sent_to_pharmacy:
            medical_record.sent_to_pharmacy = True
            medical_record.save(update_fields=['sent_to_pharmacy', 'last_updated'])
        
        return delivered_treatment
    
    def _create_or_update_referral_drug_item(self, referral, drug, quantity):
        """Create or update ReferralDispensedDrugItem for the referral"""
        # Check if drug item already exists for this referral
        existing_item = ReferralDispensedDrugItem.objects.filter(
            dispensed_drugs=referral,
            drug=drug
        ).first()
        
        if existing_item:
            # Update existing item by adding to number_of_cards
            existing_item.number_of_cards += quantity
            existing_item.save()
            print(f"[INFO] Updated existing ReferralDispensedDrugItem for {drug.name}. New number_of_cards: {existing_item.number_of_cards}")
        else:
            # Create new item
            ReferralDispensedDrugItem.objects.create(
                dispensed_drugs=referral,
                drug=drug,
                number_of_cards=quantity
            )
            print(f"[INFO] Created new ReferralDispensedDrugItem for {drug.name} with number_of_cards: {quantity}")
    
    def _calculate_total_amount(self, referral):
        """Calculate total amount for all drugs in the referral"""
        total = 0
        for delivered_treatment in referral.drugs.all():
            drug_price = delivered_treatment.drug.price_for_each or 0
            item_quantity = delivered_treatment.item_quantity or 1
            total += float(drug_price) * item_quantity
        return total

class DrugSerializer(serializers.ModelSerializer):
    class Meta:
        model = Drug
        fields = '__all__'





class WhoAdministeredSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()  # This will show the string representation of the user
    
    class Meta:
        model = who_administered
        fields = '__all__'
        depth = 1








class DeliveredMedicationTreatmentSerializer(serializers.ModelSerializer):
    who_administered = serializers.SerializerMethodField()
    
    class Meta:
        model = DeliveredMedicationTreatment
        fields = '__all__'
        depth = 1
    
    def get_who_administered(self, obj):
        # Get all who_administered records for this delivered medication
        admins = obj.nurse.all()  # Using the related_name='nurse' from the who_administered model
        return WhoAdministeredSerializer(admins, many=True).data


class PatientTreatmentHistorySerializer(serializers.ModelSerializer):
    treatments = serializers.SerializerMethodField()
    
    class Meta:
        model = MedicalRecord
        fields = '__all__'
        depth = 1
    
    def get_treatments(self, obj):
        from .serializers import TreatmentSerializer  # Import here to avoid circular import
        
        # Get all treatments for this medical record
        treatments = obj.treatments.all()
        
        # Create a custom serializer method to include delivered treatments
        class TreatmentWithDeliveriesSerializer(serializers.ModelSerializer):
            delivered_medications = serializers.SerializerMethodField()
            
            class Meta:
                model = Treatment
                fields = '__all__'
                depth = 1
            
            def get_delivered_medications(self, treatment_obj):
                # Get all delivered treatments for this treatment
                delivered = treatment_obj.delivered_treatment.all()
                return DeliveredMedicationTreatmentSerializer(delivered, many=True).data
        
        return TreatmentWithDeliveriesSerializer(treatments, many=True, context=self.context).data





class DoctorVisitCreateSerializer(serializers.ModelSerializer):
    delivered_medication_treatment_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = DoctorVisit
        fields = [
            'id', 'delivered_medication_treatment_id', 
            'observation', 'note', 'visit_date', 'visit_time'
        ]
        read_only_fields = ['id', 'visit_date', 'visit_time']

    def validate_delivered_medication_treatment_id(self, value):
        try:
            return DeliveredMedicationTreatment.objects.get(id=value)
        except DeliveredMedicationTreatment.DoesNotExist:
            raise serializers.ValidationError("Treatment not found.")

    def create(self, validated_data):
        # Get the treatment from the validated data
        treatment = validated_data.pop('delivered_medication_treatment_id')  # Changed from 'delivered_medication_treatment'
        patient = treatment.medical_record.patient  # This is the Patient model instance
    
        # Create and return the DoctorVisit instance
        return DoctorVisit.objects.create(
            delivered_medication_treatment=treatment,
            doctor=self.context['request'].user,
            patient=patient,
            **validated_data
        )





class DoctorVisitListSerializer(serializers.ModelSerializer):
    doctor_name = serializers.SerializerMethodField()
    
    class Meta:
        model = DoctorVisit
        fields = [
            'id', 'visit_date', 'visit_time', 'observation', 'note', 'doctor_name'
        ]
    
    def get_doctor_name(self, obj):
        return f"{obj.doctor.first_name} {obj.doctor.last_name}"





class PharmacyReferralListSerializer(serializers.ModelSerializer):
    patient_name = serializers.SerializerMethodField()
    referred_by_name = serializers.SerializerMethodField()
    pharmacist_name = serializers.SerializerMethodField()
    drugs = serializers.SerializerMethodField()

    class Meta:
        model = PharmacyReferral
        fields = [
            'id', 'patient', 'patient_name', 'medical_record', 'referred_by',
            'referred_by_name', 'phamacist', 'pharmacist_name', 'reason',  # Changed 'pharmacist' to 'phamacist'
            'have_pharmacist_despensed', 'have_patient_received', 'created_at',
            'drugs', 'is_payment_done', 'total_amount'
        ]
        read_only_fields = ['created_at']

    def get_patient_name(self, obj):
        return f"{obj.patient.first_name} {obj.patient.last_name}"

    def get_referred_by_name(self, obj):
        if obj.referred_by:
            return f"Dr. {obj.referred_by.first_name} {obj.referred_by.last_name}"
        return None

    def get_pharmacist_name(self, obj):
        if obj.phamacist:  # Changed to match the model's field name
            return f"{obj.phamacist.first_name} {obj.phamacist.last_name}"
        return None

    def get_drugs(self, obj):
        """Get all delivered medication treatments for this referral"""
        delivered_treatments = obj.drugs.all()
        return [{
            'id': treatment.id,
            'drug_id': treatment.drug.id,
            'drug_name': treatment.drug.name,
            'dosage': treatment.dosage,
            'frequency': treatment.frequency,
            'duration': treatment.duration,
            'item_quantity': treatment.item_quantity,
            'description': treatment.description,
            'prescribed_by': {
                'id': treatment.prescribed_by.id,
                'name': f"{treatment.prescribed_by.first_name} {treatment.prescribed_by.last_name}"
            } if treatment.prescribed_by else None,
            'date_created': treatment.date_created
        } for treatment in delivered_treatments]





class PharmacyDispenseUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PharmacyReferral
        fields = ['id', 'have_pharmacist_despensed', 'phamacist']
        read_only_fields = ['id']
    
    def update(self, instance, validated_data):
        # Set the pharmacist to the currently authenticated user
        if 'phamacist' not in validated_data:
            validated_data['phamacist'] = self.context['request'].user
        return super().update(instance, validated_data)


class PharmacyReferralPaymentUpdateSerializer(serializers.ModelSerializer):
    # Map frontend camelCase to backend snake_case
    amountPaid = serializers.CharField(source='amount_paid', required=False)
    paymentMethod = serializers.IntegerField(source='payment_method', required=False)
    
    class Meta:
        model = PharmacyReferral
        fields = ['amountPaid', 'paymentMethod', 'payment_received_by', 'is_payment_done']
        read_only_fields = ['payment_received_by', 'is_payment_done']
    
    def validate_amountPaid(self, value):
        try:
            amount = float(value)
            if amount < 0:
                raise serializers.ValidationError("Amount paid cannot be negative")
            return value
        except (ValueError, TypeError):
            raise serializers.ValidationError("Please enter a valid amount")
    
    def validate_paymentMethod(self, value):
        from .models import PaymentMethod
        # If value is already a PaymentMethod object, return it
        if isinstance(value, PaymentMethod):
            return value
        # If value is an ID (string or number), get the PaymentMethod object
        try:
            payment_method = PaymentMethod.objects.get(id=int(value))
            return payment_method
        except (PaymentMethod.DoesNotExist, TypeError, ValueError):
            raise serializers.ValidationError("Invalid payment method")
    
    def update(self, instance, validated_data):
        # Check if payment is being marked as done for the first time
        is_new_payment = not instance.is_payment_done and validated_data.get('is_payment_done', True)
        
        if is_new_payment:
            # Deduct drug quantities when payment is completed
            self._deduct_drug_quantities(instance)
            print(f"[INFO] Payment completed for referral {instance.id}. Drug quantities deducted.")
        
        # Set payment received by the current user and mark payment as done
        validated_data['payment_received_by'] = self.context['request'].user
        validated_data['is_payment_done'] = True
        return super().update(instance, validated_data)
    
    def _deduct_drug_quantities(self, referral):
        """Deduct drug quantities when payment is made"""
        for delivered_treatment in referral.drugs.all():
            drug = delivered_treatment.drug
            item_quantity = delivered_treatment.item_quantity or 1
            
            # Check if drug has enough quantity
            if drug.quantity < item_quantity:
                raise serializers.ValidationError(
                    f"Not enough stock for {drug.name}. Available: {drug.quantity}, Required: {item_quantity}"
                )
            
            # Deduct from drug quantity
            drug.quantity -= item_quantity
            drug.save()
            print(f"[INFO] Deducted {item_quantity} from {drug.name} quantity. New quantity: {drug.quantity}")






class BulkSaleIdSerializer(serializers.ModelSerializer):
    class Meta:
        model = BulkSaleId
        fields = ['id', 'bulk_id', 'is_valid']
        read_only_fields = ['id', 'bulk_id', 'created_at']





class DrugSerializer(serializers.ModelSerializer):
    class Meta:
        model = Drug
        fields = '__all__'




class DrugSaleSerializer(serializers.ModelSerializer):
    # Accept sales_id from frontend but map it to bulk_sale_id internally
    sales_id = serializers.CharField(write_only=True, required=True)
    
    class Meta:
        model = DrugSale
        fields = [
            'id', 'customer_name', 'customer_phone', 'customer_email',
            'sales_id', 'total_amount', 'amount_paid', 
            'payment_status', 'payment_method', 'payment_reference', 
            'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ('balance', 'created_at', 'updated_at', 'sold_by')
    
    def validate(self, data):
        print("\n=== Validating Data ===")
        print(f"Input data: {data}")
        
        # Ensure required fields are present
        required_fields = ['bulk_sale_id', 'items', 'customer_name', 'total_amount']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            error_msg = f"Missing required fields: {', '.join(missing_fields)}"
            print(f"Validation error: {error_msg}")
            raise serializers.ValidationError({'detail': error_msg})
        
        # Ensure amount_paid is not greater than total_amount
        amount_paid = data.get('amount_paid', 0)
        total_amount = data.get('total_amount', 0)
        items = data.get('items', [])
        
        print(f"Validating payment: amount_paid={amount_paid}, total_amount={total_amount}")
        
        if amount_paid > total_amount:
            error_msg = 'Amount paid cannot be greater than total amount'
            print(f"Validation error: {error_msg}")
            raise serializers.ValidationError({'amount_paid': error_msg})
            
        # Validate items
        if not items:
            error_msg = 'At least one item is required'
            print(f"Validation error: {error_msg}")
            raise serializers.ValidationError({'items': error_msg})
            
        for idx, item in enumerate(items):
            print(f"Validating item {idx}: {item}")
            if not isinstance(item, dict):
                error_msg = f'Item {idx} must be an object with drug and number_of_cards'
                print(f"Validation error: {error_msg}")
                raise serializers.ValidationError({'items': {str(idx): error_msg}})
                
            if 'drug' not in item or 'number_of_cards' not in item:
                error_msg = 'Each item must contain both drug ID and number_of_cards'
                print(f"Validation error: {error_msg}")
                raise serializers.ValidationError({'items': {str(idx): error_msg}})
                
            try:
                drug_id = int(item['drug'])
                number_of_cards = int(item['number_of_cards'])
                if number_of_cards <= 0:
                    raise ValueError("number_of_cards must be positive")
            except (ValueError, TypeError) as e:
                error_msg = f'Invalid value in item {idx}: {str(e)}'
                print(f"Validation error: {error_msg}")
                raise serializers.ValidationError({'items': {str(idx): str(e)}})
                
        # Set default payment_status if not provided
        if 'payment_status' not in data:
            if amount_paid <= 0:
                data['payment_status'] = 'pending'
            elif amount_paid < total_amount:
                data['payment_status'] = 'partial'
            else:
                data['payment_status'] = 'paid'
                
        print(f"Validation successful. Final data: {data}")
        print("========================\n")
        return data
    
    def validate(self, data):
        print("\n=== Validating Data ===")
        print(f"Input data: {data}")
        
        # Ensure required fields are present
        required_fields = ['sales_id', 'customer_name', 'total_amount']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            error_msg = f"Missing required fields: {', '.join(missing_fields)}"
            print(f"Validation error: {error_msg}")
            raise serializers.ValidationError({'detail': error_msg})
        
        # Ensure amount_paid is not greater than total_amount
        amount_paid = data.get('amount_paid', 0)
        total_amount = data.get('total_amount', 0)
        
        if amount_paid > total_amount:
            error_msg = 'Amount paid cannot be greater than total amount'
            print(f"Validation error: {error_msg}")
            raise serializers.ValidationError({'amount_paid': error_msg})
                
        # Set default payment_status if not provided
        if 'payment_status' not in data:
            if amount_paid <= 0:
                data['payment_status'] = 'pending'
            elif amount_paid < total_amount:
                data['payment_status'] = 'partial'
            else:
                data['payment_status'] = 'paid'
                
        print(f"Validation successful. Final data: {data}")
        return data
    
    def create(self, validated_data):
        print("\n=== Creating Drug Sale ===")
        print(f"Validated data: {validated_data}")
        
        # Extract sales_id from validated_data
        sales_id_str = validated_data.pop('sales_id')
        
        # Set the sold_by field to the current user if not provided
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated and 'sold_by' not in validated_data:
            validated_data['sold_by'] = request.user
        
        try:
            # Get the BulkSaleId instance by bulk_id string
            bulk_sale = BulkSaleId.objects.get(bulk_id=sales_id_str)
            validated_data['sales_id'] = bulk_sale
            
            print(f"Creating DrugSale with data: {validated_data}")
            
            # Create the DrugSale instance
            drug_sale = super().create(validated_data)
            print(f"Created DrugSale: {drug_sale.id}")
            
            return drug_sale
            
        except BulkSaleId.DoesNotExist as e:
            error_msg = f'Bulk sale with ID {bulk_sale_id} not found'
            print(f"Error: {error_msg}")
            raise serializers.ValidationError({'bulk_sale_id': error_msg})
            
        except Exception as e:
            import traceback
            print("Error creating DrugSale:")
            print(traceback.format_exc())
            raise serializers.ValidationError({
                'detail': f'Error creating drug sale: {str(e)}'
            })


class DrugSaleListSerializer(serializers.ModelSerializer):
    sales_id = serializers.SerializerMethodField()
    sold_by = serializers.StringRelatedField()
    
    class Meta:
        model = DrugSale
        fields = [
            'id', 'sales_id', 'customer_name', 'customer_phone', 'customer_email',
            'total_amount', 'amount_paid', 'balance', 'payment_status', 
            'payment_method', 'payment_reference', 'notes', 'created_at', 'updated_at',
            'sold_by'
        ]
        read_only_fields = fields
    
    def get_sales_id(self, obj):
        """Safely get bulk_id, handling null sales_id"""
        if obj.sales_id:
            return obj.sales_id.bulk_id
        return None



class DrugSaleDetailSerializer(serializers.ModelSerializer):
    sales_id = serializers.SerializerMethodField()
    sold_by = serializers.StringRelatedField()
    dispensed_items = serializers.SerializerMethodField()
    
    class Meta:
        model = DrugSale
        fields = [
            'id', 'sales_id', 'customer_name', 'customer_phone', 'customer_email',
            'total_amount', 'amount_paid', 'balance', 'payment_status', 
            'payment_method', 'payment_reference', 'notes', 'created_at',
            'sold_by', 'dispensed_items'
        ]
        read_only_fields = fields
    
    def get_sales_id(self, obj):
        """Safely get bulk_id, handling null sales_id"""
        if obj.sales_id:
            return obj.sales_id.bulk_id
        return None
    
    def get_dispensed_items(self, obj):
        if not obj.sales_id:
            return []
            
        dispensed_items = ReferralDispensedDrugItem.objects.filter(
            bulk_sale_id=obj.sales_id
        ).select_related('drug')
        
        return [{
            'id': item.id,
            'drug_id': item.drug.id,
            'drug_name': item.drug.name,
            'number_of_cards': item.number_of_cards,
            'unit_price': item.drug.price_for_each if hasattr(item.drug, 'price_for_each') else None,
            'total_price': (item.drug.price_for_each * item.number_of_cards) 
                          if hasattr(item.drug, 'price_for_each') and item.drug.price_for_each else None
        } for item in dispensed_items]


class TestRequestPaymentUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestRequest
        fields = ['amount', 'is_payment_done', 'payment_received_by', 'payment_method', 'status']
        read_only_fields = ['payment_received_by', 'status']
    
    def validate_amount(self, value):
        if not value or float(value) <= 0:
            raise serializers.ValidationError("Amount must be a positive number")
        return value

    def validate_payment_method(self, value):
        from .models import PaymentMethod
        # If value is already a PaymentMethod object, return it
        if isinstance(value, PaymentMethod):
            return value
        # If value is an ID, get the PaymentMethod object
        try:
            payment_method = PaymentMethod.objects.get(id=value)
            return payment_method
        except (PaymentMethod.DoesNotExist, TypeError, ValueError):
            raise serializers.ValidationError("Invalid payment method")


class DrugSalePaymentUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DrugSale
        fields = ['amount_paid', 'payment_method', 'payment_reference']
        extra_kwargs = {
            'amount_paid': {'required': True},
            'payment_method': {'required': True},
            'payment_reference': {'required': False}
        }
    
    def validate_payment_method(self, value):
        from .models import PaymentMethod
        # If value is already a PaymentMethod object, return it
        if isinstance(value, PaymentMethod):
            return value
        # If value is an ID, get the PaymentMethod object
        try:
            payment_method = PaymentMethod.objects.get(id=value)
            return payment_method
        except (PaymentMethod.DoesNotExist, TypeError, ValueError):
            raise serializers.ValidationError("Invalid payment method")


class AdmissionChargesSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdmissionCharges
        fields = ['id', 'payment_category', 'name', 'amount_paid', 'amount_to_pay', 'paid_to', 'mode_of_payment', 'description']
        read_only_fields = ['id']

class AdmissionWithChargesSerializer(serializers.ModelSerializer):
    charges = AdmissionChargesSerializer(many=True, read_only=True)
    
    class Meta:
        model = Admission
        fields = ['id', 'admission_date', 'discharge_date', 'status', 'charges']
        read_only_fields = ['id', 'admission_date', 'discharge_date', 'status', 'charges']


class AdmissionChargeCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating new admission charges
    """
    class Meta:
        model = AdmissionCharges
        fields = [
            'id', 'admission', 'payment_category', 'name', 'amount_paid', 
            'amount_to_pay', 'paid_to', 'mode_of_payment', 'description'
        ]
        read_only_fields = ['id']
        extra_kwargs = {
            'admission': {'required': True},
            'payment_category': {'required': True},
            'amount_to_pay': {'required': True},
            'paid_to': {'required': True},
            'mode_of_payment': {'required': True}
        }

    def validate_admission(self, value):
        """Validate that the admission exists"""
        if not value:
            raise serializers.ValidationError("Admission is required")
        return value

    def validate_amount_to_pay(self, value):
        """Validate that amount is positive"""
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero")
        return value

    def create(self, validated_data):
        """Create and return a new admission charge"""
        return AdmissionCharges.objects.create(**validated_data)


class AdmissionChargeUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdmissionCharges
        fields = [
            'payment_category',
            'name',
            'amount_paid',
            'amount_to_pay',  # Added the new field
            'paid_to',
            'mode_of_payment',
            'description'
        ]


class AdmissionSerializer(serializers.ModelSerializer):
    """
    Serializer for Admission model
    Provides detailed admission information for patients
    """
    patient_name = serializers.SerializerMethodField()
    patient_email = serializers.SerializerMethodField()
    admitted_by_name = serializers.SerializerMethodField()
    bed_info = serializers.SerializerMethodField()
    ward_info = serializers.SerializerMethodField()
    formatted_admission_date = serializers.SerializerMethodField()
    formatted_discharge_date = serializers.SerializerMethodField()
    total_charges = serializers.SerializerMethodField()
    
    class Meta:
        model = Admission
        fields = [
            'id',
            'patient',
            'patient_name',
            'patient_email',
            'admitted_by',
            'admitted_by_name',
            'bed',
            'bed_info',
            'ward_info',
            'number_of_stay_days',
            'is_discharged',
            'admission_date',
            'formatted_admission_date',
            'discharge_date',
            'formatted_discharge_date',
            'status',
            'total_charges'
        ]
        read_only_fields = ['id', 'admission_date', 'admitted_by']
    
    def get_patient_name(self, obj):
        return f"{obj.patient.first_name} {obj.patient.last_name}"
    
    def get_patient_email(self, obj):
        return obj.patient.email
    
    def get_admitted_by_name(self, obj):
        if obj.admitted_by:
            return f"{obj.admitted_by.first_name} {obj.admitted_by.last_name}"
        return None
    
    def get_bed_info(self, obj):
        if obj.bed:
            return {
                'id': obj.bed.id,
                'bed_number': f"Bed {obj.bed.id}",
                'room_name': obj.bed.room.name if obj.bed.room else None,
                'is_occupied': obj.bed.is_occupied
            }
        return None
    
    def get_ward_info(self, obj):
        if obj.bed and obj.bed.room and obj.bed.room.ward:
            return {
                'id': obj.bed.room.ward.id,
                'name': obj.bed.room.ward.name
            }
        return None
    
    def get_formatted_admission_date(self, obj):
        if obj.admission_date:
            return obj.admission_date.strftime('%B %d, %Y at %I:%M %p')
        return None
    
    def get_formatted_discharge_date(self, obj):
        if obj.discharge_date:
            return obj.discharge_date.strftime('%B %d, %Y at %I:%M %p')
        return None
    
    def get_total_charges(self, obj):
        """Calculate total charges for this admission"""
        total = obj.charges.aggregate(
            total=models.Sum('amount_to_pay')
        )['total'] or 0
        return float(total)


class AppointmentUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating appointment details
    Allows updating appointment date and reason
    """
    doctor_id = serializers.IntegerField(write_only=True, required=False)
    
    class Meta:
        model = Appointment
        fields = [
            'doctor_id',
            'appointment_date', 
            'patient_reason_for_appointment'
        ]
    
    def validate(self, data):
        User = get_user_model()
        appointment = self.instance
        
        # Validate doctor if provided
        if 'doctor_id' in data:
            try:
                doctor = User.objects.get(
                    id=data['doctor_id'],
                    role__name='doctor'
                )
                data['doctor'] = doctor
            except User.DoesNotExist:
                raise serializers.ValidationError(
                    {"doctor_id": "Doctor not found or invalid."}
                )
        
        # Validate appointment date if provided
        if 'appointment_date' in data:
            if data['appointment_date'] <= timezone.now():
                raise serializers.ValidationError(
                    {"appointment_date": "Appointment date must be in the future."}
                )
            
            # Check for existing appointments for the doctor at the same time
            doctor = data.get('doctor', appointment.doctor)
            if Appointment.objects.filter(
                doctor=doctor,
                appointment_date=data['appointment_date']
            ).exclude(id=appointment.id).exists():
                raise serializers.ValidationError(
                    {"appointment_date": "Doctor already has an appointment at this time."}
                )
        
        return data


class AppointmentTerminationSerializer(serializers.ModelSerializer):
    """
    Serializer for terminating appointments
    Updates status to cancelled and records who terminated the appointment
    """
    reason = serializers.CharField(
        max_length=500, 
        required=False, 
        allow_blank=True,
        help_text="Reason for appointment termination"
    )
    
    class Meta:
        model = Appointment
        fields = ['status', 'who_terminated', 'reason']
        read_only_fields = ['status', 'who_terminated']
    
    def validate(self, data):
        appointment = self.instance
        
        # Check if appointment can be terminated
        if appointment.status in ['cancelled', 'completed']:
            raise serializers.ValidationError(
                f"Cannot terminate an appointment that is already {appointment.status}."
            )
        
        return data
    
    def update(self, instance, validated_data):
        # Set the user who terminated the appointment
        user = self.context['request'].user
        instance.who_terminated = user
        instance.status = 'cancelled'
        
        # Save the appointment
        instance.save(update_fields=['status', 'who_terminated'])
        
        return instance