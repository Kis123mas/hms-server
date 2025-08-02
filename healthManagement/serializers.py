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



class PatientEMRSerializer(serializers.ModelSerializer):
    age = serializers.SerializerMethodField(read_only=True)
    bmi = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = PatientEMR
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'age', 'bmi']
    
    def get_age(self, obj):
        return obj.age
    
    def get_bmi(self, obj):
        return obj.bmi



class CreatePatientEMRSerializer(serializers.ModelSerializer):
    patient_id = serializers.PrimaryKeyRelatedField(
        queryset=APPLICATIONS_USER_MODEL.objects.filter(role__name='patient'),
        source='patient',
        required=True,
        help_text="ID of the patient for whom EMR is being created"
    )

    class Meta:
        model = PatientEMR
        fields = [
            'patient_id', 'blood_group', 'height', 'weight', 'birth_date', 'gender', 'last_blood_pressure', 'last_blood_sugar'
        ]
    
    def validate(self, data):
        # Check if patient already has an EMR
        if PatientEMR.objects.filter(patient=data['patient']).exists():
            raise serializers.ValidationError("This patient already has an EMR record")
        return data



class UpdatePatientEMRSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientEMR
        fields = [
            'blood_group', 'height', 'weight', 'birth_date', 'gender', 'last_blood_pressure', 'last_blood_sugar'
        ]
        extra_kwargs = {
            'height': {'required': False},
            'weight': {'required': False},
            'birth_date': {'required': False}
        }

    def validate(self, data):
        # Add any custom validation logic here
        return data



class PatientVitalSerializer(serializers.ModelSerializer):
    recorded_by = serializers.PrimaryKeyRelatedField(
        read_only=True,
        default=serializers.CurrentUserDefault()
    )
    
    class Meta:
        model = PatientVital
        fields = [
            'id', 'patient', 'recorded_by',
            'blood_pressure_systolic', 'blood_pressure_diastolic',
            'heart_rate', 'temperature', 'oxygen_saturation',
            'respiratory_rate', 'measurement_context', 'notes',
            'recorded_at', 'updated_at'
        ]
        read_only_fields = ['id', 'recorded_by', 'recorded_at', 'updated_at']
    
    def validate_patient(self, value):
        if value.role.name != 'patient':
            raise serializers.ValidationError("Only patients can have vital records")
        return value



class UpdatePatientVitalSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientVital
        fields = [
            'blood_pressure_systolic', 'blood_pressure_diastolic',
            'heart_rate', 'temperature', 'oxygen_saturation',
            'respiratory_rate', 'measurement_context', 'notes'
        ]
        extra_kwargs = {
            'blood_pressure_systolic': {'required': False},
            'blood_pressure_diastolic': {'required': False},
            'heart_rate': {'required': False}
        }

    def validate(self, data):
        # Validate blood pressure values
        if 'blood_pressure_systolic' in data or 'blood_pressure_diastolic' in data:
            systolic = data.get('blood_pressure_systolic', self.instance.blood_pressure_systolic)
            diastolic = data.get('blood_pressure_diastolic', self.instance.blood_pressure_diastolic)
            if systolic <= diastolic:
                raise serializers.ValidationError(
                    "Systolic pressure must be greater than diastolic"
                )
        return data




class TestResultSerializer(serializers.ModelSerializer):
    performed_by = serializers.PrimaryKeyRelatedField(
        read_only=True,
        default=serializers.CurrentUserDefault()
    )
    
    class Meta:
        model = TestResult
        fields = '__all__'
        read_only_fields = [
            'request_date', 'processing_date', 
            'completion_date', 'verified_by'
        ]

    def validate(self, data):
        # Ensure labtech can't modify certain fields
        if self.context['request'].user.role.name == 'labtech':
            if 'requesting_doctor' in data or 'verified_by' in data:
                raise serializers.ValidationError(
                    "Lab technicians cannot modify doctor fields"
                )
        return data



class DrugSerializer(serializers.ModelSerializer):
    needs_restock = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Drug
        fields = '__all__'
        read_only_fields = ['current_quantity', 'last_restocked']





class DrugUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Drug
        fields = [
            'name', 'generic_name', 'description', 'category',
            'dosage_form', 'strength', 'manufacturer', 'barcode',
            'current_quantity', 'minimum_stock', 'unit_of_measure',
            'unit_price', 'selling_price', 'ndc_code', 'expiry_date'
        ]
        extra_kwargs = {
            'barcode': {'required': False},
            'ndc_code': {'required': False},
            'expiry_date': {'required': False}
        }

    def validate_current_quantity(self, value):
        if value < 0:
            raise serializers.ValidationError("Quantity cannot be negative")
        return value

    def validate(self, data):
        if 'selling_price' in data and 'unit_price' in data:
            if data['selling_price'] < data['unit_price']:
                raise serializers.ValidationError("Selling price cannot be less than unit price")
        return data

