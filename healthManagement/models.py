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
            height_m = self.height_cm / 100
            return round(self.weight_kg / (height_m ** 2), 1)
        return None