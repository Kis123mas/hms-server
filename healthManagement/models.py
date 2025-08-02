from django.db import models
from django.utils import timezone
from django.conf import settings
from decimal import Decimal

class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,  # Use Django's settings instead
        on_delete=models.CASCADE,
        related_name='profile'
    )
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
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
    appointment_date = models.DateTimeField()
    reason = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
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
    TEST_STATUS = [
        ('REQUESTED', 'Requested'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('VERIFIED', 'Verified'),
        ('CANCELLED', 'Cancelled'),
    ]

    TEST_CATEGORIES = [
        ('HEMATOLOGY', 'Hematology'),
        ('BIOCHEMISTRY', 'Biochemistry'),
        ('MICROBIOLOGY', 'Microbiology'),
        ('PATHOLOGY', 'Pathology'),
        ('RADIOLOGY', 'Radiology'),
        ('CARDIOLOGY', 'Cardiology'),
    ]

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
    test_category = models.CharField(max_length=20, choices=TEST_CATEGORIES)
    status = models.CharField(max_length=20, choices=TEST_STATUS, default='REQUESTED')

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
        return f"{self.test_name} - {self.patient} ({self.status})"

    def save(self, *args, **kwargs):
        # Update status dates automatically
        if self.status == 'IN_PROGRESS' and not self.processing_date:
            self.processing_date = timezone.now()
        elif self.status == 'COMPLETED' and not self.completion_date:
            self.completion_date = timezone.now()
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


