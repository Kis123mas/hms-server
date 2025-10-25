from django.db import models
from healthManagement.models import Profile
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager, Group
from django.utils import timezone


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, first_name=None, last_name=None, role=None, is_superuser=False):
        if not email:
            raise ValueError('Users must have an email address')
        email = self.normalize_email(email)
        user = self.model(email=email, first_name=first_name, last_name=last_name, role=role, is_superuser=is_superuser)
        user.set_password(password)
        user.save(using=self._db)
        
        # Only create profile for non-superusers
        if not is_superuser:
            # Lazy import to avoid circular dependency
            from healthManagement.models import Profile
            
            # Create profile only if it doesn't exist
            if not hasattr(user, 'profile'):
                Profile.objects.create(user=user)
        return user

    def create_superuser(self, email, password, first_name=None, last_name=None, role=None):
        # Create user with is_superuser=True
        user = self.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            role=role,
            is_superuser=True
        )
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True  # Ensure superuser is active by default
        user.save(using=self._db)
        
        # Create profile for superuser if it doesn't exist
        from healthManagement.models import Profile
        if not hasattr(user, 'profile'):
            Profile.objects.create(user=user)
            
        return user

class CustomUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True, max_length=255)
    first_name = models.CharField(max_length=64, blank=True, null=True)
    last_name = models.CharField(max_length=64, blank=True, null=True)
    role = models.ForeignKey(Group, on_delete=models.SET_NULL, null=True, blank=True)
    is_active = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_on_duty = models.BooleanField(default=False)
    last_login = models.DateTimeField(blank=True, null=True)
    date_joined = models.DateTimeField(default=timezone.now)
    is_online = models.BooleanField(
        default=False,
        help_text="Indicates if the user is currently online"
    )
    last_seen = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last time the user was active"
    )

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    def __str__(self):
        return self.email



