from django.db import models
from django.utils import timezone
from django.conf import settings
from django.core.validators import MinValueValidator




class Income(models.Model):
    """Model to track income transactions."""
    reason = models.CharField(max_length=255, blank=True, null=True, verbose_name='reason')
    handled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name='income_transactions',
        verbose_name='recorded by'
    )
    received_from = models.CharField(max_length=255, verbose_name='received from')
    payment_method = models.CharField(
        max_length=20,
        choices=[
            ('cash', 'Cash'),
            ('card', 'Credit/Debit Card'),
            ('bank', 'Bank Transfer'),
            ('insurance', 'Insurance'),
            ('other', 'Other')
        ],
        default='cash',
        verbose_name='payment method'
    )
    amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
        help_text='Amount in local currency'
    )
    description = models.TextField(blank=True)
    date = models.DateField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date', '-created_at']
        verbose_name = 'Income Record'
        verbose_name_plural = 'Income Records'
    
    def __str__(self):
        return f"Income of ${self.amount} from {self.received_from} on {self.date}"


class Expense(models.Model):
    """Model to track expense transactions."""
    reason = models.CharField(max_length=255, blank=True, null=True, verbose_name='reason')
    handled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name='expense_transactions',
        verbose_name='recorded by'
    )
    paid_to = models.CharField(max_length=255, verbose_name='paid to')
    amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
        help_text='Amount in local currency'
    )
    description = models.TextField(blank=True)
    date = models.DateField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    payment_method = models.CharField(
        max_length=20,
        choices=[
            ('cash', 'Cash'),
            ('check', 'Check'),
            ('bank', 'Bank Transfer'),
            ('card', 'Credit/Debit Card'),
            ('other', 'Other')
        ],
        default='bank'
    )
    receipt_number = models.CharField(max_length=100, blank=True, null=True)
    
    class Meta:
        ordering = ['-date', '-created_at']
        verbose_name = 'Expense Record'
        verbose_name_plural = 'Expense Records'
    
    def __str__(self):
        return f"{self.amount} - {self.paid_to}"


class Activity(models.Model):
    """
    Tracks all actions performed across healthManagement and accountant apps
    """
    ACTION_CHOICES = [
        ('read', 'Read'),
        ('create', 'Created'),
        ('update', 'Updated'),
        ('delete', 'Deleted'),
    ]

    action_taken_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='actions_taken'
    )

    action_taken_on = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='actions_received'
    )

    action = models.CharField(
        max_length=10,
        choices=ACTION_CHOICES
    )

    model_name = models.CharField(max_length=100)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    description = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        actor = f"{self.action_taken_by}" if self.action_taken_by else "System"
        receiver = f" on {self.action_taken_on}" if self.action_taken_on else ""
        return f"{actor} - {self.get_action_display()} {self.model_name}{receiver}"
