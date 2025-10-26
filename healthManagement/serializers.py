from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils.dateparse import parse_datetime
from django.contrib.auth.models import Group
from django.db.models import Count, Q, Prefetch
from .models import *
from django.utils import timezone

APPLICATIONS_USER_MODEL = get_user_model()


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
