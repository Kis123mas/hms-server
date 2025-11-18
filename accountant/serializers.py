from rest_framework import serializers
from .models import *
from django.contrib.auth import get_user_model
from datetime import datetime, timedelta
from healthManagement.models import *
from django.db.models import *

APPLICATIONS_USER_MODEL = get_user_model()

class PeriodSummarySerializer(serializers.Serializer):
    period = serializers.CharField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    total_income = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_expenses = serializers.DecimalField(max_digits=12, decimal_places=2)
    net_balance = serializers.DecimalField(max_digits=12, decimal_places=2)
    
    class Meta:
        fields = ['period', 'start_date', 'end_date', 'total_income', 'total_expenses', 'net_balance']


class FinancialSummarySerializer(serializers.Serializer):
    daily = PeriodSummarySerializer()
    weekly = PeriodSummarySerializer()
    monthly = PeriodSummarySerializer()
    yearly = PeriodSummarySerializer()
    
    class Meta:
        fields = ['daily', 'weekly', 'monthly', 'yearly']

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = APPLICATIONS_USER_MODEL
        fields = ['id', 'first_name', 'last_name', 'email']
        read_only_fields = fields
        
class NonSuperuserUserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    
    class Meta:
        model = APPLICATIONS_USER_MODEL
        fields = ['id', 'email', 'first_name', 'last_name', 'full_name', 'role']
        read_only_fields = fields
    
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip()
    
    def get_role(self, obj):
        # Return the name of the role (Group) if it exists
        return obj.role.name if obj.role else "No Role"

class IncomeSerializer(serializers.ModelSerializer):
    handled_by = UserSerializer(read_only=True)
    
    class Meta:
        model = Income
        fields = [
            'id',
            'reason',
            'handled_by',
            'received_from',
            'payment_method',
            'amount',
            'description',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']



class ExpenseSerializer(serializers.ModelSerializer):
    handled_by = UserSerializer(read_only=True)
    
    class Meta:
        model = Expense
        fields = [
            'id',
            'reason',
            'amount',
            'description',
            'payment_method',
            'paid_to',
            'handled_by',
            'receipt_number',
            'date',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'handled_by']


class CreateExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        fields = [
            'reason',
            'amount',
            'description',
            'payment_method',
            'paid_to',
            'receipt_number',
            'date'
        ]
        extra_kwargs = {
            'reason': {'required': True},
            'amount': {'required': True},
            'payment_method': {'required': True},
            'paid_to': {'required': True},
            'description': {'required': False},
            'receipt_number': {'required': False},
            'date': {'required': False}
        }

    def create(self, validated_data):
        # Set the handled_by to the current user
        validated_data['handled_by'] = self.context['request'].user
        return super().create(validated_data)



class UserProfileSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    profile = serializers.SerializerMethodField()
    
    class Meta:
        model = APPLICATIONS_USER_MODEL
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'role', 'is_active', 'is_staff', 'is_on_duty', 'last_login',
            'date_joined', 'is_online', 'last_seen', 'profile'
        ]
        read_only_fields = fields
    
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip()
    
    def get_role(self, obj):
        return obj.role.name if obj.role else "No Role"
    
    def get_profile(self, obj):
        if not hasattr(obj, 'profile'):
            return None
            
        profile = obj.profile
        request = self.context.get('request')
        
        # Build absolute URLs for file fields if request is available
        def get_absolute_url(url):
            if url and request:
                return request.build_absolute_uri(url)
            return url
        
        return {
            'phone_number': profile.phone_number,
            'address': profile.address,
            'date_of_birth': profile.date_of_birth,
            'gender': profile.gender,
            'marital_status': profile.marital_status,
            'blood_group': profile.blood_group,
            'genotype': profile.genotype,
            'national_id': profile.national_id,
            'emergency_contact': profile.emergency_contact,
            'next_of_kin': profile.next_of_kin,
            'relationship_to_next_of_kin': profile.relationship_to_next_of_kin,
            'profile_picture': get_absolute_url(profile.profile_picture.url) if profile.profile_picture else None,
            'document_1': get_absolute_url(profile.document_1.url) if profile.document_1 else None,
            'document_2': get_absolute_url(profile.document_2.url) if profile.document_2 else None,
            'document_3': get_absolute_url(profile.document_3.url) if profile.document_3 else None,
            'document_4': get_absolute_url(profile.document_4.url) if profile.document_4 else None,
            'specialization': profile.specialization,
            'license_number': profile.license_number,
            'department': profile.department.name if profile.department else None,
            'department_id': profile.department.id if profile.department else None,
            'employment_date': profile.employment_date,
            'qualification': profile.qualification,
            'bio': profile.bio,
            'is_admitted': profile.is_admitted,
            'created_at': profile.created_at,
            'updated_at': profile.updated_at
        }


class UserRoleUpdateSerializer(serializers.ModelSerializer):
    role_id = serializers.IntegerField(required=True, write_only=True)
    
    class Meta:
        model = APPLICATIONS_USER_MODEL
        fields = ['role_id']
    
    def validate_role_id(self, value):
        """Check if the role exists"""
        from django.contrib.auth.models import Group
        if not Group.objects.filter(id=value).exists():
            raise serializers.ValidationError("Role with this ID does not exist")
        return value
    
    def update(self, instance, validated_data):
        role_id = validated_data.pop('role_id')
        from django.contrib.auth.models import Group
        try:
            role = Group.objects.get(id=role_id)
            instance.role = role
            instance.save()
            return instance
        except Group.DoesNotExist:
            raise serializers.ValidationError("Role not found")





class AppointmentSerializer(serializers.ModelSerializer):
    """
    Serializer for Appointment model
    """
    patient_name = serializers.SerializerMethodField()
    doctor_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    start_time = serializers.SerializerMethodField()
    end_time = serializers.SerializerMethodField()
    
    class Meta:
        model = Appointment
        fields = [
            'id', 'patient', 'patient_name', 'doctor', 'doctor_name', 
            'appointment_date', 'start_time', 'end_time', 'status', 'status_display',
            'patient_reason_for_appointment', 'is_patient_available',
            'is_vitals_taken', 'is_doctor_done_with_patient',
            'is_doctor_with_patient', 'is_medical_history_recorded',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_patient_name(self, obj):
        return f"{obj.patient.first_name} {obj.patient.last_name}" if obj.patient else None
    
    def get_doctor_name(self, obj):
        return f"{obj.doctor.first_name} {obj.doctor.last_name}" if obj.doctor else None
    
    def get_start_time(self, obj):
        if obj.appointment_date:
            try:
                return obj.appointment_date.strftime('%I:%M %p')
            except (AttributeError, ValueError):
                return None
        return None
    
    def get_end_time(self, obj):
        if obj.appointment_date:
            try:
                # Assuming 1 hour appointment duration, you can adjust this as needed
                from datetime import timedelta
                end_time = obj.appointment_date + timedelta(hours=1)
                return end_time.strftime('%I:%M %p')
            except (AttributeError, ValueError):
                return None
        return None


class WardSerializer(serializers.ModelSerializer):
    """
    Serializer for Ward model with room count
    """
    room_count = serializers.SerializerMethodField()
    total_beds = serializers.SerializerMethodField()
    
    class Meta:
        model = Ward
        fields = ['id', 'name', 'room_count', 'total_beds']
    
    def get_room_count(self, obj):
        """Get the number of rooms in this ward"""
        return obj.rooms.count()
    
    def get_total_beds(self, obj):
        """Get the total number of beds in all rooms of this ward"""
        return Room.objects.filter(ward=obj).aggregate(total=models.Sum('bed_count'))['total'] or 0




class DrugSerializer(serializers.ModelSerializer):
    """
    Serializer for Drug model
    """
    
    class Meta:
        model = Drug
        fields = [
            'id', 
            'name', 
            'dosage', 
            'quantity', 
            'price_for_each', 
            'form', 
            'manufacturer',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']
        extra_kwargs = {
            'name': {'required': False},
            'dosage': {'required': False},
            'quantity': {'required': False},
            'price_for_each': {'required': False},
            'form': {'required': False},
            'manufacturer': {'required': False},
        }
    
    def validate_quantity(self, value):
        """Ensure quantity is not negative"""
        if value is not None and value < 0:
            raise serializers.ValidationError("Quantity cannot be negative.")
        return value
    
    def validate_price_for_each(self, value):
        """Ensure price is not negative"""
        if value is not None and value < 0:
            raise serializers.ValidationError("Price cannot be negative.")
        return value