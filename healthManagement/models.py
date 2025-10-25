from django.db import models
from django.utils import timezone
from django.conf import settings
from decimal import Decimal
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



class PatientEMR(models.Model):
    BLOOD_GROUP_CHOICES = [
        ('A+', 'A+'), ('A-', 'A-'),
        ('B+', 'B+'), ('B-', 'B-'),
        ('AB+', 'AB+'), ('AB-', 'AB-'),
        ('O+', 'O+'), ('O-', 'O-')
    ]
    
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
        ('U', 'Undisclosed')
    ]

    # Primary Relationship
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='patient_emr',
        limit_choices_to={'role__name': 'patient'}
    )

    # Biometric Data
    blood_group = models.CharField(
        max_length=3,
        choices=BLOOD_GROUP_CHOICES,
        blank=True
    )
    height = models.PositiveSmallIntegerField(
        help_text="Height in cm",
        blank=True,
        null=True
    )
    weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Weight in kg",
        blank=True,
        null=True
    )
    birth_date = models.DateField(blank=True, null=True)
    gender = models.CharField(
        max_length=1,
        choices=GENDER_CHOICES,
        blank=True
    )


    # Vital Stats
    last_blood_pressure = models.CharField(
        max_length=7,
        blank=True,
        help_text="Format: '120/80'"
    )
    last_blood_sugar = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        blank=True,
        null=True,
        help_text="Fasting glucose in mg/dL"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Electronic Medical Record"
        verbose_name_plural = "Electronic Medical Records"

    def __str__(self):
        return f"EMR - {self.patient.first_name}"

    @property
    def age(self):
        if self.birth_date:
            today = timezone.now().date()
            return today.year - self.birth_date.year - (
                (today.month, today.day) < 
                (self.birth_date.month, self.birth_date.day)
            )
        return None

    @property
    def bmi(self):
        if self.height and self.weight:
            height_m = Decimal(self.height) / Decimal(100)  # Convert height to meters
            # Ensure both weight and height_m are Decimal before division
            return float(Decimal(self.weight) / (height_m ** Decimal(2)))
        return None



class PatientVital(models.Model):
    # Relationship Fields
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='patient_vitals',
        limit_choices_to={'role__name': 'patient'}  # Only patients can have vitals
    )
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recorded_vitals',
        limit_choices_to={'role__name__in': ['doctor', 'nurse']}  # Only medical staff
    )

    # Core Vital Signs (Required)
    blood_pressure_systolic = models.PositiveSmallIntegerField(
        verbose_name="Systolic BP (mmHg)"
    )
    blood_pressure_diastolic = models.PositiveSmallIntegerField(
        verbose_name="Diastolic BP (mmHg)"
    )
    heart_rate = models.PositiveSmallIntegerField(
        verbose_name="Heart Rate (bpm)"
    )
    temperature = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        verbose_name="Temperature (°C)"
    )

    # Optional Measurements
    oxygen_saturation = models.PositiveSmallIntegerField(
        blank=True,
        null=True,
        verbose_name="SpO2 (%)"
    )
    respiratory_rate = models.PositiveSmallIntegerField(
        blank=True,
        null=True,
        verbose_name="Respiratory Rate (breaths/min)"
    )

    # Context Fields
    measurement_context = models.CharField(
        max_length=20,
        choices=[
            ('RESTING', 'Resting'),
            ('POST_EXERCISE', 'Post-Exercise'),
            ('FASTING', 'Fasting'),
            ('POST_PRANDIAL', 'After Meal')
        ],
        default='RESTING'
    )
    notes = models.TextField(blank=True)

    # Timestamps
    recorded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-recorded_at']
        verbose_name = "Patient Vital Signs"
        verbose_name_plural = "Patient Vital Signs Records"
        permissions = [
            ('view_all_vitals', 'Can view all patients vitals'),
        ]

    def __str__(self):
        return f"Vitals for {self.patient} ({self.recorded_at})"

    @property
    def blood_pressure(self):
        return f"{self.blood_pressure_systolic}/{self.blood_pressure_diastolic}"

    def save(self, *args, **kwargs):
        """Auto-set recorded_by if not specified"""
        if not self.recorded_by and hasattr(self, '_current_user'):
            self.recorded_by = self._current_user
        super().save(*args, **kwargs)



class TestResult(models.Model):

    # Relationships
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='patient_tests',
        limit_choices_to={'role__name': 'patient'}
    )
    requesting_doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='requested_tests',
        limit_choices_to={'role__name': 'doctor'}
    )
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='performed_tests',
        limit_choices_to={'role__name': 'labtech'}
    )
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_tests',
        limit_choices_to={'role__name__in': ['doctor', 'labtech']}
    )

    # Test Information
    test_name = models.CharField(max_length=100)
    test_code = models.CharField(max_length=20)

    # Dates
    request_date = models.DateTimeField(auto_now_add=True)
    collection_date = models.DateTimeField(null=True, blank=True)
    processing_date = models.DateTimeField(null=True, blank=True)
    completion_date = models.DateTimeField(null=True, blank=True)

    # Results
    results = models.JSONField(
        default=dict,
        help_text="Structured test results data"
    )
    reference_ranges = models.JSONField(
        blank=True, null=True,
        help_text="Normal reference ranges"
    )
    abnormal_flags = models.JSONField(
        blank=True, null=True,
        help_text="Abnormal result indicators"
    )

    # Documents
    report_file = models.FileField(
        upload_to='test_reports/%Y/%m/%d/',
        blank=True, null=True
    )
    raw_data_files = models.JSONField(
        blank=True, null=True,
        help_text="Array of raw data file paths"
    )

    # Clinical Information
    clinical_notes = models.TextField(blank=True, null=True)
    interpretation = models.TextField(blank=True, null=True)
    recommendations = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-request_date']
        permissions = [
            ('can_process_test', 'Can process lab tests'),
            ('can_verify_test', 'Can verify test results'),
        ]

    def __str__(self):
        return f"{self.test_name} - {self.patient}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    @property
    def is_abnormal(self):
        return bool(self.abnormal_flags)

    @property
    def turnaround_time(self):
        if self.completion_date and self.request_date:
            return self.completion_date - self.request_date
        return None



class Drug(models.Model):
    CATEGORY_CHOICES = [
        ('ANTIBIOTIC', 'Antibiotic'),
        ('ANALGESIC', 'Pain Reliever'),
        ('ANTIHYPERTENSIVE', 'Blood Pressure'),
        ('ANTIDIABETIC', 'Diabetes'),
        ('OTHER', 'Other'),
    ]
    
    name = models.CharField(max_length=100)
    generic_name = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    dosage_form = models.CharField(max_length=50)  # tablet, capsule, injection, etc.
    strength = models.CharField(max_length=50)  # 500mg, 10mg/ml, etc.
    manufacturer = models.CharField(max_length=100, blank=True)
    barcode = models.CharField(max_length=50, unique=True, blank=True, null=True)
    
    # Quantity Tracking
    current_quantity = models.PositiveIntegerField(default=0)
    minimum_stock = models.PositiveIntegerField(default=10)
    unit_of_measure = models.CharField(max_length=20, default='units')
    
    # Pricing
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Regulatory
    ndc_code = models.CharField(max_length=20, blank=True)  # National Drug Code
    expiry_date = models.DateField(blank=True, null=True)
    
    last_restocked = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} {self.strength} ({self.current_quantity} {self.unit_of_measure} available)"
    
    @property
    def needs_restock(self):
        return self.current_quantity < self.minimum_stock

    class Meta:
        ordering = ['name']
        verbose_name_plural = "Drug Inventory"



class Prescription(models.Model):
    # Core Relationships
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='patient_prescriptions',
        limit_choices_to={'role__name': 'patient'}
    )
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='doctor_prescriptions',
        limit_choices_to={'role__name': 'doctor'}
    )
    pharmacist = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pharmacist_dispensations',
        limit_choices_to={'role__name': 'pharmacist'}
    )

    # Prescription Details
    medications = models.ManyToManyField(
        Drug,
        related_name='prescriptions',
        blank=True,
        help_text="Medications prescribed"
    )
    instructions = models.TextField()
    piad = models.BooleanField(default=False)
    # Status Tracking
    is_dispensed = models.BooleanField(default=False, verbose_name="Pharmacy Dispensed")
    is_collected = models.BooleanField(default=False, verbose_name="Patient Collected")
    notes = models.TextField(blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    issued_at = models.DateTimeField(null=True, blank=True)
    dispensed_at = models.DateTimeField(null=True, blank=True)
    collected_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        permissions = [
            ('can_dispense', 'Can mark prescription as dispensed'),
            ('can_collect', 'Can mark prescription as collected'),
        ]

    def __str__(self):
        medication_names = ", ".join([med.name for med in self.medications.all()[:3]])
        if self.medications.count() > 3:
            medication_names += f" (+{self.medications.count() - 3} more)"
        return f"{medication_names} for {self.patient.first_name}"

    def save(self, *args, **kwargs):
        # Track when pharmacy dispenses
        if self.is_dispensed and not self.dispensed_at:
            self.dispensed_at = timezone.now()
            if hasattr(self, '_dispensing_pharmacist'):
                self.pharmacist = self._dispensing_pharmacist
        
        # Track when patient collects
        if self.is_collected and not self.collected_at:
            if not self.is_dispensed:
                raise ValueError("Cannot collect undispensed prescription")
            self.collected_at = timezone.now()
        
        super().save(*args, **kwargs)

    @property
    def status_flow(self):
        return {
            'created': self.created_at,
            'issued': self.issued_at,
            'dispensed': self.dispensed_at,
            'collected': self.collected_at
        }

    @property
    def current_responsible_party(self):
        if self.is_collected:
            return "Patient has collected"
        elif self.is_dispensed:
            return f"Waiting for patient collection (prepared by {self.pharmacist})"
        elif self.issued_at:
            return f"Awaiting pharmacy dispensing (prescribed by {self.doctor})"
        return "In draft status"


class Ward(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

    def total_rooms(self):
        return self.rooms.count()

    def total_beds(self):
        return sum(room.total_beds() for room in self.rooms.all())


class Room(models.Model):
    ward = models.ForeignKey(Ward, related_name='rooms', on_delete=models.CASCADE)
    number = models.CharField(max_length=10)
    bed_count = models.PositiveIntegerField()

    class Meta:
        unique_together = ('ward', 'number')

    def __str__(self):
        return f"Room {self.number} - {self.ward.name}"

    def total_beds(self):
        return self.beds.count()

    def clean(self):
        if self.pk and self.beds.count() > self.bed_count:
            raise ValidationError(
                f"Room {self.number} already has {self.beds.count()} beds. "
                f"Cannot set bed_count lower than that."
            )


class AllocateBed(models.Model):
    room = models.ForeignKey(Room, related_name='beds', on_delete=models.CASCADE)
    bed_number = models.CharField(max_length=10)
    is_occupied = models.BooleanField(default=False)
    allocated_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='allocated_beds'
    )
    allocated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='beds_allocated'
    )
    allocated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('room', 'bed_number')
        constraints = [
            models.UniqueConstraint(
                fields=['allocated_to'],
                condition=models.Q(is_occupied=True),
                name='unique_patient_allocation'
            )
        ]

    def __str__(self):
        return f"Bed {self.bed_number} in {self.room}"

    def clean(self):
        existing_beds = AllocateBed.objects.filter(room=self.room).exclude(pk=self.pk).count()
        if existing_beds >= self.room.bed_count:
            raise ValidationError(
                f"Cannot allocate more than {self.room.bed_count} beds in Room {self.room.number}"
            )
        
        # Prevent a patient from being allocated to multiple beds
        if self.allocated_to:
            existing_allocation = AllocateBed.objects.filter(
                allocated_to=self.allocated_to,
                is_occupied=True
            ).exclude(pk=self.pk)
            
            if existing_allocation.exists():
                existing_bed = existing_allocation.first()
                raise ValidationError(
                    f"Patient {self.allocated_to.email} is already allocated to "
                    f"Bed {existing_bed.bed_number} in {existing_bed.room}. "
                    f"A patient cannot be allocated to multiple beds."
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


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

