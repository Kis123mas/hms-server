from django.db import models
from django.utils import timezone
from django.conf import settings
from decimal import Decimal
import random
import string

from django.utils import timezone
from django.core.exceptions import ValidationError


class VerificationCode(models.Model):
    """
    Account verification Code
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - {self.code}"


class ActiveWebSocketConnection(models.Model):
    """
    Model to track active WebSocket connections
    Stores user email when they connect and removes when they disconnect
    """
    email = models.EmailField(unique=True)
    connected_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-connected_at']

    def __str__(self):
        return f"{self.email} - Connected at {self.connected_at}"


class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name



class Profile(models.Model):
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile'
    )

    phone_number = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=10, choices=[('male','Male'),('female','Female'),('other','Other')], blank=True, null=True)
    marital_status = models.CharField(max_length=20, choices=[('single','Single'),('married','Married'),('divorced','Divorced'),('widowed','Widowed')], blank=True, null=True)
    blood_group = models.CharField(max_length=3, choices=[('A+','A+'),('A-','A-'),('B+','B+'),('B-','B-'),('AB+','AB+'),('AB-','AB-'),('O+','O+'),('O-','O-')], blank=True, null=True)
    genotype = models.CharField(max_length=5, choices=[
        ('AA', 'AA'), 
        ('AS', 'AS'), 
        ('SS', 'SS'),
        ('AC', 'AC'),
        ('SC', 'SC'),
        ('CC', 'CC')
    ], blank=True, null=True, help_text='Genetic blood composition')
    national_id = models.CharField(max_length=30, blank=True, null=True)
    emergency_contact = models.CharField(max_length=50, blank=True, null=True)
    next_of_kin = models.CharField(max_length=100, blank=True, null=True)
    relationship_to_next_of_kin = models.CharField(max_length=50, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    document_1 = models.FileField(upload_to='profile_documents/', blank=True, null=True)
    document_2 = models.FileField(upload_to='profile_documents/', blank=True, null=True)
    document_3 = models.FileField(upload_to='profile_documents/', blank=True, null=True)
    document_4 = models.FileField(upload_to='profile_documents/', blank=True, null=True)
    specialization = models.CharField(max_length=100, blank=True, null=True)
    license_number = models.CharField(max_length=50, blank=True, null=True)
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="profiles"
    )
    employment_date = models.DateField(blank=True, null=True)  # staff
    qualification = models.CharField(max_length=200, blank=True, null=True)  # staff
    bio = models.TextField(blank=True, null=True)
    is_admitted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile of {self.user.email}"





class Appointment(models.Model):

   
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]

    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='patient_appointments',
        limit_choices_to={'role__name': 'patient'}
    )
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='doctor_appointments',
        limit_choices_to={'role__name': 'doctor'}
    )
    nurse = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name="nurse_appointment_vitals",
        limit_choices_to={'role__name': 'nurse'}
    )
    is_patient_available = models.BooleanField(default=False)
    is_vitals_taken = models.BooleanField(default=False)
    is_doctor_done_with_patient = models.BooleanField(default=False)
    is_doctor_with_patient = models.BooleanField(default=False)
    patient_reason_for_appointment = models.TextField()
    who_terminated = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="terminated_appointments"
    )
    is_medical_history_recorded = models.BooleanField(default=False)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    appointment_date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-appointment_date']
        unique_together = ['doctor', 'appointment_date']

    def __str__(self):
        return f"Appointment #{self.id} - {self.patient} with Dr. {self.doctor}"




class Notification(models.Model):
    """
    Notification model with sender and receiver
    """
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='sent_notifications',
        null=True,
        blank=True,
        help_text="User who sent the notification (optional)"
    )
    receivers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='received_notifications',
        help_text="Users who will receive the notification"
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_read']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        sender = self.sender.email if self.sender else 'System'
        receiver_count = self.receivers.count()
        return f"{self.title} - From: {sender} To: {receiver_count} recipient(s)"




class VitalSign(models.Model):
    """Stores the vital readings for a patient."""
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='patient_vital_signs',
        limit_choices_to={'role__name': 'patient'}
    )
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    recorded_at = models.DateTimeField(auto_now_add=True)

    temperature_c = models.DecimalField(max_digits=4, decimal_places=1, help_text="Body temperature in Celsius")
    pulse_rate = models.PositiveIntegerField(help_text="Heart rate in beats per minute (bpm)")
    respiratory_rate = models.PositiveIntegerField(help_text="Breaths per minute")
    systolic_bp = models.PositiveIntegerField(help_text="Systolic blood pressure (mmHg)")
    diastolic_bp = models.PositiveIntegerField(help_text="Diastolic blood pressure (mmHg)")
    oxygen_saturation = models.DecimalField(max_digits=4, decimal_places=1, help_text="SpO₂ percentage")
    weight_kg = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    height_cm = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-recorded_at']

    def __str__(self):
        return f"Vitals for {self.patient} at {self.recorded_at.strftime('%Y-%m-%d %H:%M')}"

    def bmi(self):
        """Calculate BMI if weight and height are provided."""
        if self.weight_kg and self.height_cm:
            # Convert both values to float for consistent division
            weight = float(self.weight_kg)
            height_m = float(self.height_cm) / 100.0  # Convert cm to m
            if height_m > 0:  # Prevent division by zero
                return round(weight / (height_m ** 2), 1)
        return None


class MedicalRecord(models.Model):
    """
    Tracks patient medical diagnoses and treatments.
    """
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('resolved', 'Resolved'),
        ('chronic', 'Chronic'),
    ]

    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='medical_records',
        limit_choices_to={'role__name': 'patient'}
    )
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='treated_patients',
        limit_choices_to={'role__name': 'doctor'}
    )
    
    # Core medical information
    diagnosis = models.CharField(max_length=255)
    symptoms = models.TextField()
    is_treatment_created = models.BooleanField(default=False)
    requested_for_test = models.BooleanField(default=False)
    sent_to_pharmacy = models.BooleanField(default=False)
    is_test_result_ready = models.BooleanField(default=False)
    notes = models.TextField(blank=True, null=True)
    
    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active'
    )
    date_created = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    date_resolved = models.DateField(blank=True, null=True)
    
    # Optional references
    appointment = models.ForeignKey(
        'Appointment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='medical_records'
    )
    vital_signs = models.OneToOneField(
        'VitalSign',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='medical_record'
    )

    class Meta:
        ordering = ['-date_created']

    def __str__(self):
        return f"{self.patient.email}: {self.diagnosis} ({self.get_status_display()})"
    
    def save(self, *args, **kwargs):
        # Update resolved date when status changes to resolved
        if self.status == 'resolved' and not self.date_resolved:
            self.date_resolved = timezone.now().date()
        super().save(*args, **kwargs)





class Treatment(models.Model):
    """
    Tracks individual treatments prescribed to a patient as part of a medical record.
    """
    TREATMENT_TYPES = [
        ('medication', 'Medication'),
        ('surgery', 'Surgery'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    medical_record = models.ForeignKey(
        MedicalRecord,
        on_delete=models.CASCADE,
        related_name='treatments',
        help_text='The medical record this treatment is associated with'
    )
    
    treatment_type = models.CharField(
        max_length=50,
        choices=TREATMENT_TYPES,
        help_text='Type of treatment being administered'
    )
    
    name = models.CharField(
        max_length=255,
        help_text='Name/description of the treatment (e.g., medication name, therapy type)'
    )

    
    start_date = models.DateField(
        default=timezone.now,
        help_text='When the treatment should begin'
    )
    
    end_date = models.DateField(
        blank=True,
        null=True,
        help_text='Expected or actual end date of the treatment (if applicable)'
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text='Current status of the treatment'
    )
    
    notes = models.TextField(
        blank=True,
        null=True,
        help_text='Additional notes or instructions about the treatment'
    )
    
    prescribed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='prescribed_treatments',
        limit_choices_to={'role__name': 'doctor'},
        help_text='Doctor who prescribed this treatment'
    )
    
    date_created = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date_created']
        verbose_name = 'Treatment'
        verbose_name_plural = 'Treatments'

    def __str__(self):
        return f"{self.get_treatment_type_display()}: {self.name} for {self.medical_record.patient.email}"
    
    def save(self, *args, **kwargs):
        # If no end date is provided and treatment is completed, set end date to now
        if self.status == 'completed' and not self.end_date:
            self.end_date = timezone.now().date()
        super().save(*args, **kwargs)


class SurgeryPlacement(models.Model):
    """
    Tracks surgical procedures and their basic details.
    """
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    treatment = models.OneToOneField(
        Treatment,
        on_delete=models.CASCADE,
        related_name='surgery_placement',
        limit_choices_to={'treatment_type': 'surgery'}
    )
    
    medical_record = models.ForeignKey(
        MedicalRecord,
        on_delete=models.CASCADE,
        related_name='surgeries'
    )
    
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='surgeries',
        null=True,
        blank=True,
        limit_choices_to={'role__name': 'patient'},
        help_text='Patient who will undergo the surgery'
    )
    
    surgeon = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='surgeries_performed',
        limit_choices_to={'role__name': 'doctor'}
    )
    
    surgery_type = models.CharField(
        max_length=200,
        help_text='Type of surgical procedure'
    )
    
    scheduled_date = models.DateField()
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='scheduled'
    )
    
    notes = models.TextField(
        blank=True,
        null=True,
        help_text='Any additional notes about the surgery'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-scheduled_date']

    def __str__(self):
        return f"{self.surgery_type} - {self.get_status_display()}"
    
    def save(self, *args, **kwargs):
        if self.treatment_id and self.treatment.treatment_type != 'surgery':
            raise ValidationError('Associated treatment must be of type "surgery"')
        
        # Set the patient from the medical record if not set
        if not self.patient_id and self.medical_record_id:
            self.patient = self.medical_record.patient
            
        super().save(*args, **kwargs)




class Ward(models.Model):
    """
    create ward
    """
    name = models.CharField(max_length=100)
    description = models.TextField()
    
    def __str__(self):
        return self.name
    

class  Room(models.Model):
    """
    create room
    """
    name = models.CharField(max_length=100)
    description = models.TextField()
    bed_count = models.IntegerField()
    ward = models.ForeignKey(Ward, on_delete=models.CASCADE, related_name='rooms')
    
    def __str__(self):
        return self.name




class Bed(models.Model):
    """Bed model representing a bed in a room"""
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='beds',
        limit_choices_to={'role__name': 'patient'}
    )
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='beds')
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    is_occupied = models.BooleanField(default=False)

    
    def __str__(self):
        if self.patient and self.is_occupied:
            return f"Bed {self.id} in {self.room.name} - Occupied by {self.patient.email}"
        return f"Bed {self.id} in {self.room.name} - Available"










class Admission(models.Model):
    """Tracks patient admissions to beds"""
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('discharged', 'Discharged'),
        ('transferred', 'Transferred'),
    ]
    
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='admissions',
        null=True,
        blank=True,
        limit_choices_to={'role__name': 'patient'}
    )
    admitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='admitted_patients',
        limit_choices_to={'role__name__in': ['doctor', 'nurse', 'admin']}
    )
    bed = models.OneToOneField(
        'Bed',
        on_delete=models.CASCADE,
        related_name='admission',
        null=True,
        blank=True
    )
    number_of_stay_days = models.IntegerField(null=True, blank=True)
    is_discharged = models.BooleanField(default=False)
    admission_date = models.DateTimeField(auto_now_add=True)
    discharge_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active'
    )
    
    class Meta:
        ordering = ['-admission_date']
    
    def __str__(self):
        return f"{self.patient.email} - {self.bed} ({self.status})"
    
    def clean(self):
        # No validations - allow any assignment
        pass

    def save(self, *args, **kwargs):
        # Just save without any validations or additional logic
        super().save(*args, **kwargs)



class AdmissionChargeCategory(models.Model):
    name = models.CharField(max_length=255, unique=True, blank=False, null=False)
    description = models.TextField(blank=True, null=True)
    price = models.CharField(max_length=255, blank=False, null=False)

    def __str__(self):
        return self.name




class AdmissionCharges(models.Model):
    """Tracks admission charges"""
    PAYMENT_METHODS = [
        ('cash', 'Cash'),
        ('card', 'Card'),
        ('online', 'Online'),
        ('other', 'Other')
    ]
    admission = models.ForeignKey(
        'Admission',
        on_delete=models.CASCADE,
        related_name='charges',
        null=True,
        blank=True
    )
    charge_category = models.ForeignKey(
        'AdmissionChargeCategory',
        on_delete=models.CASCADE,
        related_name='charges',
        null=True,
        blank=True
    )
    name = models.CharField(max_length=255, blank=True, null=True)
    amount_to_pay = models.DecimalField(max_digits=10, blank=True, null=True, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=10, blank=True, null=True, decimal_places=2)
    paid_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank = True,
    )
    mode_of_payment = models.CharField(
        max_length=20,
        choices=PAYMENT_METHODS,
        default='cash'
    )
    description = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.name



class TestTypes(models.Model):
    name = models.CharField(max_length=255, unique=True, blank=False, null=False)
    description = models.TextField(blank=True, null=True)
    price = models.CharField(max_length=255, blank=False, null=False)

    def __str__(self):
        return self.name




class PaymentMethod(models.Model):
    name = models.CharField(max_length=255, blank=True, null=True)
    account_number = models.CharField(max_length=255, blank=True, null=True)
    bank = models.CharField(max_length=255, blank=True, null=True)
    account_name = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.name




class TestRequest(models.Model):
    """Model to track test requests from doctors to lab technicians"""
    
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ]
    
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='test_requests',
        limit_choices_to={'role__name': 'patient'}
    )
    customers_name = models.CharField(max_length=255, blank=True, null=True, help_text="Name of the customer")
    customers_phone = models.CharField(max_length=20, blank=True, null=True, help_text="Customer's phone number")
    customers_email = models.EmailField(blank=True, null=True, help_text="Customer's email address")
    medical_record = models.ForeignKey(
        MedicalRecord,
        on_delete=models.CASCADE,
        related_name='test_for_confirmation',
        null=True,
        blank=True
    )
    test_type = models.ForeignKey(
        TestTypes,
        on_delete=models.CASCADE,
        related_name='test_requests',
        null=True,
        blank=True
    )
    test_name = models.CharField(
        max_length=200,
        help_text="Name of the specific test"
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='ordered_tests',
        limit_choices_to={'role__name__in': ['doctor', 'nurse', 'labtech']}
    )
    lab_tehnician = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='received_request',
        limit_choices_to={'role__name': 'labtech'}
    )
    amount = models.CharField(max_length=100, blank=True, null=True)
    payment_received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='received_payment',
        limit_choices_to={'role__name': 'accountant'}
    )
    payment_method = models.ForeignKey(
        PaymentMethod,
        on_delete=models.CASCADE,
        related_name='test_requests',
        null=True,
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    notes = models.TextField(blank=True, null=True)
    is_payment_done = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        if self.patient:
            return f"{self.patient.email}"
        return f"TestRequest {self.id} - {self.customers_name or 'No patient'}"




class TestResult(models.Model):
    """Model to store detailed test results with standard medical fields"""
    RESULT_STATUS = [
        ('normal', 'Normal'),
        ('abnormal', 'Abnormal'),
        ('critical', 'Critical'),
        ('inconclusive', 'Inconclusive')
    ]
    
    test_request = models.OneToOneField(
        TestRequest,
        on_delete=models.CASCADE,
        related_name='result'
    )
    
    # Standard result fields
    test_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Numeric test result value"
    )
    unit = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Unit of measurement (e.g., mg/dL, mmol/L)"
    )
    reference_range = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Normal reference range (e.g., 12.0-15.5 g/dL)"
    )
    result_status = models.CharField(
        max_length=20,
        choices=RESULT_STATUS,
        help_text="Interpretation of the test result"
    )
    findings = models.TextField(
        blank=True,
        null=True,
        help_text="Detailed findings and observations"
    )
    conclusion = models.TextField(
        blank=True,
        null=True,
        help_text="Conclusion or summary of the test results"
    )
    
    # Metadata
    result_date = models.DateTimeField(
        default=timezone.now,
        help_text="Date and time when test was completed"
    )
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='performed_tests',
        limit_choices_to={'role__name': 'labtech'},
        help_text="Lab technician who performed the test"
    )
    # Review fields removed as per request
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-result_date']
    
    def save(self, *args, **kwargs):
        # Update the related test request status when result is created
        if not self.pk:  # Only on creation
            self.test_request.status = 'completed'
            self.test_request.save()
            
        # Review-related logic removed
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.test_request.test_name} - {self.get_result_status_display()} ({self.test_request.patient.get_full_name() or self.test_request.patient.email})"
    
    @property
    def formatted_result(self):
        """Return a formatted string of the test result"""
        if self.test_value is not None:
            unit = f" {self.unit}" if self.unit else ""
            ref_range = f" (Ref: {self.reference_range})" if self.reference_range else ""
            return f"{self.test_value}{unit}{ref_range}"
        return self.findings or "No results recorded"




# i need drug model here
class Drug(models.Model):
    """
    Model to represent a medication or drug
    """
    name = models.CharField(max_length=255, help_text='Name of the drug')
    dosage = models.CharField(max_length=100, help_text='Dosage information (e.g., 500mg)')
    quantity = models.PositiveIntegerField(default=1, help_text='Quantity of drugs referred')
    price_for_each = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text='Price per drug unit')
    form = models.CharField(max_length=100, help_text='Form of the drug (e.g., Tablet, Syrup)')
    manufacturer = models.CharField(max_length=255, help_text='Manufacturer of the drug')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name



class BulkSaleId(models.Model):
    staff = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='bulk_sale_ids',
        limit_choices_to={'role__name': 'pharmacy'}
    )
    bulk_id = models.CharField(
        max_length=6,  # Set to 6 characters
        unique=True,
        null=True,
        blank=True,
        help_text='6-character alphanumeric code to group items from the same sale'
    )
    is_valid = models.BooleanField(
        default=True,
        help_text='Indicates if the bulk sale ID is valid'
    )
    
    def generate_bulk_id(self):
        """Generate a random 6-character alphanumeric code with both upper and lowercase letters"""
        while True:
            # Generate a random 6-character code
            chars = string.ascii_letters + string.digits  # A-Z, a-z, 0-9
            code = ''.join(random.choices(chars, k=6))
            
            # Check if code already exists
            if not BulkSaleId.objects.filter(bulk_id=code).exists():
                return code
    
    def save(self, *args, **kwargs):
        if not self.bulk_id:  # Only generate if bulk_id is not set
            self.bulk_id = self.generate_bulk_id()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.bulk_id or f"BulkSale-{self.id}"
    

class ReferralDispensedDrugItem(models.Model):
    """
    Through model to track individual drugs and their card counts in a dispensation.
    """
    dispensed_drugs = models.ForeignKey(
        'PharmacyReferral',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='referral_dispensed_items'
    )
    bulk_sale_id = models.ForeignKey(
        BulkSaleId,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='referral_dispensed_items'
    )
    drug = models.ForeignKey(
        Drug,
        on_delete=models.CASCADE,
        related_name='referral_dispensed_items'
    )
    number_of_cards = models.PositiveIntegerField(
        default=1,
        help_text='Number of cards dispensed for this drug'
    )

    class Meta:
        unique_together = ('dispensed_drugs', 'drug')

    def __str__(self):
        return f"{self.drug.name} - {self.number_of_cards} cards"






class DeliveredMedicationTreatment(models.Model):
    """
    Tracks delivered treatments and their details.
    """
    treatment = models.ForeignKey(
        Treatment,
        on_delete=models.CASCADE,
        related_name='delivered_treatment'
    )
    medical_record = models.ForeignKey(
        MedicalRecord,
        on_delete=models.CASCADE,
        related_name='delivered_treatments'
    )
    # map from drug model
    drug = models.ForeignKey(
        Drug,
        on_delete=models.CASCADE,
        related_name='delivered_treatments'
    )
    item_quantity = models.IntegerField(default=1)
    description = models.TextField()
    dosage = models.CharField(max_length=100)
    frequency = models.CharField(max_length=100)
    duration = models.CharField(max_length=100)
    prescribed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='delivered_treatments',
        limit_choices_to={'role__name': 'doctor'}
    )
    
    date_created = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date_created']

    def __str__(self):
        return f"Delivered Treatment: {self.drug} for {self.treatment.medical_record.patient.email}"







class PharmacyReferral(models.Model):
    """
    Model to track referrals to the pharmacy for medication dispensing
    """

    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='pharmacy_referrals',
        limit_choices_to={'role__name': 'patient'}
    )
    medical_record = models.ForeignKey(
        MedicalRecord,
        on_delete=models.CASCADE,
        related_name='pharmacy_referrals',
        null=True,
        blank=True,
        help_text='Medical record associated with the referral'
    )
    referred_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='pharmacy_referrals_made',
        limit_choices_to={'role__name': 'doctor'}
    )
    phamacist = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pharmacist_referrals',
        limit_choices_to={'role__name': 'pharmacy'}
    )
    have_pharmacist_despensed = models.BooleanField(default=False)
    have_patient_received = models.BooleanField(default=False)
    reason = models.TextField(help_text='Reason for pharmacy referral')
    total_amount = models.CharField(max_length=100, default=0)
    drugs = models.ManyToManyField(
        'DeliveredMedicationTreatment', 
        related_name='pharmacy_referral_drugs',
        blank=True
    )
    amount_paid = models.CharField(max_length=100, default=0)
    payment_method = models.ForeignKey(
        PaymentMethod,
        on_delete=models.CASCADE,
        related_name='pharmacy_referrals',
        null=True,
        blank=True
    )    
    payment_received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pharmacy_referrals_received',
        limit_choices_to={'role__name': 'accountant'}
    )
    is_payment_done = models.BooleanField(default=False, help_text='Payment status')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Pharmacy Referral for {self.patient} - {self.reason}"




class DrugSale(models.Model):
    """
    Model to track drug sales to unadmitted customers
    """
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('partial', 'Partially Paid'),
        ('paid', 'Fully Paid'),
        ('cancelled', 'Cancelled')
    ]
    
    
    customer_name = models.CharField(max_length=255, help_text="Name of the customer")
    customer_phone = models.CharField(max_length=20, blank=True, null=True, help_text="Customer's phone number")
    customer_email = models.EmailField(blank=True, null=True, help_text="Customer's email address")
    sales_id = models.ForeignKey(
        BulkSaleId,
        on_delete=models.CASCADE,
        related_name='drug_sales',
        null=True,
        blank=True,
        help_text='Drug sold'
    )
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='pending'
    )
    payment_method = models.ForeignKey(
        PaymentMethod,
        on_delete=models.CASCADE,
        related_name='drug_sales',
        null=True,
        blank=True
    )

    payment_reference = models.CharField(max_length=100, blank=True, null=True)
    
    sold_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='drug_sales',
        limit_choices_to={'role__name': 'pharmacy'}
    )
    payment_received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='drug_sales_payment_received_by',
        limit_choices_to={'role__name': 'accountant'}
    )
    
    notes = models.TextField(blank=True, null=True, help_text="Any additional notes about the sale")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Drug Sale'
        verbose_name_plural = 'Drug Sales'
    
    def __str__(self):
        return f"Sale #{self.id} - {self.customer_name} - {self.total_amount}"
    
    def save(self, *args, **kwargs):
        # Calculate balance whenever the model is saved
        self.balance = self.total_amount - self.amount_paid
        
        # Update payment status based on amounts
        if self.amount_paid <= 0:
            self.payment_status = 'pending'
        elif self.balance <= 0:
            self.payment_status = 'paid'
        elif self.amount_paid < self.total_amount:
            self.payment_status = 'partial'
        
        super().save(*args, **kwargs)
    
    def update_totals(self):
        """
        Update the total amount based on sold items
        """
        total = sum(item.subtotal for item in self.sold_items.all())
        self.total_amount = total
        self.balance = total - self.amount_paid
        self.save(update_fields=['total_amount', 'balance'])




class who_administered(models.Model):
  
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='who_administered'
    )
    delivered_medication_treatment = models.ForeignKey(
        DeliveredMedicationTreatment,
        on_delete=models.CASCADE,
        related_name='nurse'
    )
    preobservation = models.TextField(blank=True, null=True)
    postobservation = models.TextField(blank=True, null=True)
    nurse_administered = models.BooleanField(default=False)
    patient_received = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.user.email




class DoctorVisit(models.Model):
    delivered_medication_treatment = models.ForeignKey(
        DeliveredMedicationTreatment,
        on_delete=models.CASCADE,
        related_name='doctor_visit'
    )
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={'role__name': 'doctor'},
        related_name='doctor_visit'
    )
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={'role__name': 'patient'},
        null=True,
        blank=True,
        related_name='patient_visit'
    )
    visit_date = models.DateTimeField(auto_now_add=True)
    visit_time = models.DateTimeField(auto_now_add=True)
    observation = models.TextField(blank=True, null=True)
    note = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-visit_date']

    def __str__(self):
        return self.doctor.email


