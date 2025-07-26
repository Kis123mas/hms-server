from django.db import models
from django.utils import timezone
from django.conf import settings

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